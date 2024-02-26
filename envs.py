# FILE UPLOAD
FILE_UPLOAD_PATH = "./uploaded_files"

# DATABASE ENDPOINT
QDRANTDB_URL = "http://103.176.178.107:6333"
DB_BATCH_SIZE = 256
DB_TIMEOUT = 60

# BM25
ENABLE_BM25 = False
BM25_TOP_K = 100

# EMBEDDING MODEL
EMBEDDING_MODEL = "bkai-foundation-models/vietnamese-bi-encoder"
EMBEDDING_DIM = 768
EMBEDDING_MAX_LENGTH = 256
EMBEDDING_TOP_K = 3

# LLM API ENDPOINT
LLM_MODEL = "google/gemma-7b-it"
TGI_URL = "http://localhost:10025"
API_KEY = "hf_sample_api_key"
MAX_ANSWER_LENGTH = 4096
MAX_MODEL_LENGTH = 8192
REPETITION_PENALTY = 1.0
if "mix" in LLM_MODEL.lower():
    SEPERATORS = "<end_of_turn>\n<start_of_turn>model\n|<end_of_turn>\n<start_of_turn>user\n|<start_of_turn>user\n"
    STOP_WORDS = ["<end_of_turn>"]
elif "gem" in LLM_MODEL.lower():
    SEPERATORS = "[/INST]|</s> [INST]|<s> [INST]"
    STOP_WORDS = ["</s>"]
else:
    raise NotImplementedError
    
# FAQ HYPERPARAMETERS
FAQ_FILE = "data/hcmut_data_faq_v2.csv"
FAQ_THRESHOLD = 80
FAQ_TEMPERATURE = 0.2
FAQ_TOP_P = 0.95
FAQ_TOP_K = 50
FAQ_QUERY_TEMPLATE = """Câu hỏi: {query}
Trả lời: {answer}"""
if "mix" in LLM_MODEL.lower():
    FAQ_PROMPT = """<s> [INST] Bạn là một trợ lý thông minh. Hãy thực hiện các yêu cầu hoặc trả lời câu hỏi từ người dùng bằng tiếng Việt.
Hãy viết lại câu trả lời theo một cách khác dùng thông tin bên dưới.
{query} [/INST]
Câu trả lời mới: """
elif "gem" in LLM_MODEL.lower():
    FAQ_PROMPT = """<start_of_turn>user
Hãy viết lại câu trả lời theo một cách khác dùng thông tin bên dưới.
{query}
<end_of_turn>
<start_of_turn>model
Câu trả lời mới: """
else:
    raise NotImplementedError


# WEB HYPERPARAMETERS
WEB_FILE = "data/hcmut_data_web.csv"
WEB_THRESHOLD = 50
WEB_TEMPERATURE = 0.1
WEB_TOP_P = 0.95
WEB_TOP_K = 50
if "mix" in LLM_MODEL.lower():
    WEB_PROMPT = """<s> [INST] Trả lời câu hỏi bằng ngữ cảnh cho sẵn.
Ngữ cảnh: '''
{join(documents, "\n")}
'''
Câu hỏi: {query} [/INST]
Trả lời: """
elif "gem" in LLM_MODEL.lower():
    WEB_PROMPT = """<start_of_turn>user
Trả lời câu hỏi bằng ngữ cảnh cho sẵn.
Ngữ cảnh: '''
{join(documents, "\n")}
'''
Câu hỏi: {query}
<end_of_turn>
<start_of_turn>model
Trả lời: """
else:
    raise NotImplementedError
    

FREE_PROMPT = """{query}"""

# OTHERS
WARNING_NOTES = [
    "----------\nXin lưu ý rằng câu trả lời phía trên được sinh ra hoàn toàn từ mô hình ngôn ngữ lớn và không có trong dữ liệu của tôi. Do đó, câu trả lời có thể chứa thông tin sai sự thật hoặc lỗi thời.",
    "----------\nLưu ý: Câu trả lời có thể sai sự thật hoặc lỗi thời do không có trong dữ liệu của chúng tôi.",
]

DEFAULT_ANSWERS = [
    "Xin lỗi! Tôi chưa có dữ liệu về câu hỏi bạn yêu cầu. Vui lòng thử lại hoặc tìm kiếm thông tin trên trang web chính thức của trường: https://hcmut.edu.vn",
    "Rất tiếc, tôi chưa có câu trả lời cho yêu cầu của bạn. Vui lòng thử lại hoặc tìm kiếm thông tin trên trang web chính thức của trường: https://hcmut.edu.vn",
    "Tôi chưa hiểu câu hỏi của bạn. Vui lòng thử lại hoặc tìm kiếm thông tin trên trang web chính thức của trường: https://hcmut.edu.vn",
]
