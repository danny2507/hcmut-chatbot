# HCMUT Chatbot

## How to install
```
pip install requirements.txt
```

## Developing mode
```
python main.py --dev
```

## Production mode
- **Step 1:** Run TGI
```
text-generation-launcher \
    --model-id ura-hcmut/ura-llama-2.1-8b \
    --port 10025 \
    --watermark-gamma 0.25 \
    --watermark-delta 2 \
    --max-input-tokens 4096 \
    --max-total-tokens 8192 \
    --max-batch-prefill-tokens 8242 \
    --trust-remote-code \
    --cuda-memory-fraction 0.8
```
- **Step 2:** Start the application
```
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

or

python main.py
```
