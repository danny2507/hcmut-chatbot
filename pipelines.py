# SETTING UP PIPELINE
#####################################################################################
import re
import random
import logging
from envs import *
from haystack import Pipeline
from haystack.schema import Answer
from haystack.nodes import PromptModel, PromptNode, PromptTemplate
from haystack.nodes import (
    BM25Retriever,
    EmbeddingRetriever,
    SentenceTransformersRanker,
    Docs2Answers,
    TextConverter,
    FileTypeClassifier,
    PDFToTextConverter,
    MarkdownConverter,
    DocxToTextConverter,
)
from invocation_layer import HFInferenceEndpointInvocationLayer
from custom_plugins import DocumentThreshold
from database import initialize_db
from type_2_helpers import execute_type_2_query

logger = logging.getLogger(__name__)


class ChatbotPipeline:
    def __init__(self, document_store):
        if ENABLE_BM25:
            retriever = BM25Retriever(document_store=document_store, top_k=BM25_TOP_K)

        embedding_retriever = EmbeddingRetriever(
            document_store=document_store,
            embedding_model=EMBEDDING_MODEL,
            model_format="sentence_transformers",
            top_k=EMBEDDING_TOP_K,
            max_seq_len=EMBEDDING_MAX_LENGTH
        )

        faq_threshold = DocumentThreshold(threshold=FAQ_THRESHOLD)
        web_threshold = DocumentThreshold(threshold=WEB_THRESHOLD)
        docs2answers = Docs2Answers()

        prompt_template_paraphrase = PromptTemplate(
            prompt=FAQ_PROMPT, output_parser={"type": "AnswerParser"}
        )

        prompt_template_ask = PromptTemplate(
            prompt=WEB_PROMPT, output_parser={"type": "AnswerParser"}
        )

        prompt_template_free = PromptTemplate(
            prompt=FREE_PROMPT, output_parser={"type": "AnswerParser"}
        )

        prompt_model = PromptModel(
            model_name_or_path=TGI_URL,
            api_key=API_KEY,
            max_length=MAX_ANSWER_LENGTH,
            invocation_layer_class=HFInferenceEndpointInvocationLayer,
            model_kwargs={
                "model_max_length": MAX_MODEL_LENGTH,
                "max_new_tokens": MAX_ANSWER_LENGTH,
                "repetition_penalty": REPETITION_PENALTY,
                "stream": True,
            },
        )

        prompt_paraphrase = PromptNode(
            model_name_or_path=prompt_model,
            default_prompt_template=prompt_template_paraphrase,
            api_key=API_KEY,
            max_length=MAX_ANSWER_LENGTH,
            top_k=FAQ_TOP_K,
            stop_words=STOP_WORDS,
            model_kwargs={
                "model_max_length": MAX_MODEL_LENGTH,
                "max_new_tokens": MAX_ANSWER_LENGTH,
                "temperature": FAQ_TEMPERATURE,
                "top_p": FAQ_TOP_P,
                "repetition_penalty": REPETITION_PENALTY,
                "stream": True,
            },
        )

        prompt_ask = PromptNode(
            model_name_or_path=prompt_model,
            default_prompt_template=prompt_template_ask,
            api_key=API_KEY,
            max_length=MAX_ANSWER_LENGTH,
            top_k=WEB_TOP_K,
            stop_words=STOP_WORDS,
            model_kwargs={
                "model_max_length": MAX_MODEL_LENGTH,
                "max_new_tokens": MAX_ANSWER_LENGTH,
                "temperature": WEB_TEMPERATURE,
                "top_p": WEB_TOP_P,
                "repetition_penalty": REPETITION_PENALTY,
                "stream": True,
            },
        )

        prompt_free = PromptNode(
            model_name_or_path=prompt_model,
            default_prompt_template=prompt_template_free,
            api_key=API_KEY,
            max_length=MAX_ANSWER_LENGTH,
            top_k=WEB_TOP_K,
            stop_words=STOP_WORDS,
            model_kwargs={
                "model_max_length": MAX_MODEL_LENGTH,
                "max_new_tokens": MAX_ANSWER_LENGTH,
                "temperature": WEB_TEMPERATURE,
                "top_p": WEB_TOP_P,
                "repetition_penalty": REPETITION_PENALTY,
                "stream": True,
            },
        )

        self.faq_pipeline = Pipeline()
        self.faq_params = {"EmbeddingRetriever": {"index": "faq"}}
        if ENABLE_BM25:
            self.faq_pipeline.add_node(
                component=retriever, name="Retriever", inputs=["Query"]
            )
            self.faq_params["Retriever"] = {"index": "faq"}
        self.faq_pipeline.add_node(
            component=embedding_retriever,
            name="EmbeddingRetriever",
            inputs=["Query" if not ENABLE_BM25 else "Retriever"],
        )
        self.faq_pipeline.add_node(
            component=faq_threshold, name="Threshold", inputs=["EmbeddingRetriever"]
        )
        self.faq_pipeline.add_node(
            component=docs2answers, name="Answer", inputs=["Threshold"]
        )

        if FAQ_ENABLE_PARAPHRASING:
            self.paraphrase_pipeline = Pipeline()
            self.paraphrase_pipeline.add_node(
                component=prompt_paraphrase, name="prompt_node", inputs=["Query"]
            )

        self.web_pipeline = Pipeline()
        self.web_params = {"EmbeddingRetriever": {"index": "web"}}
        if ENABLE_BM25:
            self.web_pipeline.add_node(
                component=retriever, name="Retriever", inputs=["Query"]
            )
            self.web_params["Retriever"] = {"index": "web"}
        self.web_pipeline.add_node(
            component=embedding_retriever,
            name="EmbeddingRetriever",
            inputs=["Query" if not ENABLE_BM25 else "Retriever"],
        )
        self.web_pipeline.add_node(
            component=web_threshold, name="Threshold", inputs=["EmbeddingRetriever"]
        )

        self.llm_pipeline = Pipeline()
        self.llm_pipeline.add_node(
            component=prompt_ask, name="prompt_node", inputs=["Query"]
        )

        self.fallback_pipeline = Pipeline()
        self.fallback_pipeline.add_node(
            component=prompt_free, name="prompt_node", inputs=["Query"]
        )

    def __call__(self, query, **kwargs):
        return self.run(query, **kwargs)

    def run(self, query, **kwargs):
        llm_params = {}
        if "params" in kwargs:
            llm_params.update(kwargs["params"])
        kwargs["params"] = {}

        for note in WARNING_NOTES:
            query = query.replace(note, "")
        conversation = re.split(SEPERATORS, query)
        conversation = [x.strip() for x in conversation if x.strip() != ""]
        context = "\n".join(conversation[:-1]).strip()
        question = conversation[-1]

        kwargs["params"].update(self.faq_params)
        faq_ans = self.faq_pipeline.run(question, **kwargs)
        # Detect if  type 2 was found
        if faq_ans["documents"][0].meta.get("type") == 2:
            func  = faq_ans["documents"][0].meta["function"]
            params = faq_ans["documents"][0].meta["params"]
            faq_ans["answers"][0].answer = execute_type_2_query(func, params)

        # If there is no FAQ found
        if len(faq_ans["answers"]) == 0 or faq_ans["answers"][0].answer.strip() == "":
            kwargs["params"].update(self.web_params)
            web_ans = self.web_pipeline.run(context + "\n" + question, **kwargs)

            kwargs["params"].pop("EmbeddingRetriever", None)
            if "Retriever" in kwargs["params"]:
                kwargs["params"].pop("Retriever", None)
            kwargs["params"].update({"prompt_node": {"generation_kwargs": llm_params}})

            if len(web_ans["documents"]) > 0:
                llm_ans = self.llm_pipeline.run(
                    question, documents=web_ans["documents"], **kwargs
                )
                return llm_ans

            # Fallback only LLM
            fallback_ans = self.fallback_pipeline.run(query, **kwargs)
            warning = random.choice(WARNING_NOTES)
            fallback_ans["answers"][0].answer += f"\n\n{warning}"
            return fallback_ans
            
        if FAQ_ENABLE_PARAPHRASING:
            kwargs["params"].pop("EmbeddingRetriever", None)
            if "Retriever" in kwargs["params"]:
                kwargs["params"].pop("Retriever", None)
            kwargs["params"].update({"prompt_node": {"generation_kwargs": llm_params}})
            template = FAQ_QUERY_TEMPLATE.format(
                query=question, answer=faq_ans["answers"][0].answer
            )
            paraphrased_ans = self.paraphrase_pipeline.run(template, **kwargs)
            return paraphrased_ans
        else:
            return faq_ans


def get_index_pipeline(document_store, preprocessor, embedding_retriever):
    file_type_classifier = FileTypeClassifier()
    text_converter = TextConverter()
    pdf_converter = PDFToTextConverter()
    md_converter = MarkdownConverter()
    docx_converter = DocxToTextConverter()

    # This is an indexing pipeline
    index_pipeline = Pipeline()
    index_pipeline.add_node(
        component=file_type_classifier, name="FileTypeClassifier", inputs=["File"]
    )
    index_pipeline.add_node(
        component=text_converter,
        name="TextConverter",
        inputs=["FileTypeClassifier.output_1"],
    )
    index_pipeline.add_node(
        component=pdf_converter,
        name="PdfConverter",
        inputs=["FileTypeClassifier.output_2"],
    )
    index_pipeline.add_node(
        component=md_converter,
        name="MarkdownConverter",
        inputs=["FileTypeClassifier.output_3"],
    )
    index_pipeline.add_node(
        component=docx_converter,
        name="DocxConverter",
        inputs=["FileTypeClassifier.output_4"],
    )

    index_pipeline.add_node(
        component=preprocessor,
        name="Preprocessor",
        inputs=["TextConverter", "PdfConverter", "MarkdownConverter", "DocxConverter"],
    )
    index_pipeline.add_node(
        component=embedding_retriever,
        name="EmbeddingRetriever",
        inputs=["Preprocessor"],
    )
    index_pipeline.add_node(
        component=document_store,
        name="DocumentStore",
        inputs=["EmbeddingRetriever"],
    )

    return index_pipeline


def setup_pipelines(args):
    # Re-import the configuration variables
    from rest_api import config  # pylint: disable=reimported
    from rest_api.controller.utils import RequestLimiter

    pipelines = {}
    document_store, preprocessor = initialize_db(args)

    # Load query pipeline & document store
    print("[+] Setting up pipeline...")
    pipelines["query_pipeline"] = ChatbotPipeline(document_store)

    if args.reindex:
        print("[+] Updating document embedding...")
        document_store.update_embeddings(
            pipelines["query_pipeline"].faq_pipeline.get_node("EmbeddingRetriever"),
            index="faq",
            batch_size=DB_BATCH_SIZE,
        )
        document_store.update_embeddings(
            pipelines["query_pipeline"].web_pipeline.get_node("EmbeddingRetriever"),
            index="web",
            batch_size=DB_BATCH_SIZE,
        )
    pipelines["document_store"] = document_store

    # Setup concurrency limiter
    concurrency_limiter = RequestLimiter(config.CONCURRENT_REQUEST_PER_WORKER)
    logger.info(
        "Concurrent requests per worker: %s", config.CONCURRENT_REQUEST_PER_WORKER
    )
    pipelines["concurrency_limiter"] = concurrency_limiter

    # Load indexing pipeline
    index_pipeline = get_index_pipeline(
        document_store,
        preprocessor=preprocessor,
        embedding_retriever=pipelines["query_pipeline"].web_pipeline.get_node(
            "EmbeddingRetriever"
        ),
    )
    if not index_pipeline:
        logger.warning(
            "Indexing Pipeline is not setup. File Upload API will not be available."
        )
        # Create directory for uploaded files
        os.makedirs(FILE_UPLOAD_PATH, exist_ok=True)
    pipelines["indexing_pipeline"] = index_pipeline

    return pipelines
