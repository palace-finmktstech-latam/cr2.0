(venv) C:\Users\bencl\Proyectos\cr2.0\backend\agentic>adk web
C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\cli\fast_api.py:177: UserWarning: [EXPERIMENTAL] InMemoryCredentialService: This feature is experimental and may change or be removed in future versions without notice. It may introduce breaking changes at any time.
  credential_service = InMemoryCredentialService()
C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\auth\credential_service\in_memory_credential_service.py:33: UserWarning: [EXPERIMENTAL] BaseCredentialService: This feature is experimental and may change or be removed in future versions without notice. It may introduce breaking changes at any time.
  super().__init__()
INFO:     Started server process [37836]
INFO:     Waiting for application startup.

+-----------------------------------------------------------------------------+
| ADK Web Server started                                                      |
|                                                                             |
| For local testing, access at http://127.0.0.1:8000.                         |
+-----------------------------------------------------------------------------+

INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:54836 - "GET / HTTP/1.1" 307 Temporary Redirect
INFO:     127.0.0.1:54836 - "GET /list-apps?relative_path=./ HTTP/1.1" 200 OK
INFO:     127.0.0.1:54836 - "POST /apps/contract_reader_agent/users/user/sessions HTTP/1.1" 200 OK
INFO:     127.0.0.1:54836 - "GET /apps/contract_reader_agent/eval_sets HTTP/1.1" 200 OK
INFO:     127.0.0.1:58392 - "GET /apps/contract_reader_agent/eval_results HTTP/1.1" 200 OK
INFO:     127.0.0.1:58392 - "GET /apps/contract_reader_agent/users/user/sessions HTTP/1.1" 200 OK
INFO:     127.0.0.1:58392 - "GET /apps/contract_reader_agent/users/user/sessions HTTP/1.1" 200 OK
INFO:     127.0.0.1:58392 - "POST /run_sse HTTP/1.1" 200 OK
2025-10-02 10:11:56,305 - INFO - envs.py:47 - Loaded .env file for contract_reader_agent at C:\Users\bencl\Proyectos\cr2.0\backend\.env
2025-10-02 10:11:56,306 - INFO - envs.py:47 - Loaded .env file for contract_reader_agent at C:\Users\bencl\Proyectos\cr2.0\backend\.env
2025-10-02 10:11:57,692 - INFO - agent_loader.py:126 - Found root_agent in contract_reader_agent.agent
C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\cli\adk_web_server.py:450: UserWarning: [EXPERIMENTAL] App: This feature is experimental and may change or be removed in future versions without notice. It may introduce breaking changes at any time.
  agentic_app = App(
2025-10-02 10:11:59,116 - INFO - google_llm.py:122 - Sending out request, model: gemini-2.0-flash-exp, backend: GoogleLLMVariant.VERTEX_AI, stream: False
2025-10-02 10:11:59,117 - INFO - models.py:8185 - AFC is enabled with max remote calls: 10.
2025-10-02 10:12:03,857 - INFO - _client.py:1740 - HTTP Request: POST https://us-central1-aiplatform.googleapis.com/v1beta1/projects/contract-reader-2-dev/locations/us-central1/publishers/google/models/gemini-2.0-flash-exp:generateContent "HTTP/1.1 200 OK"
2025-10-02 10:12:03,862 - INFO - google_llm.py:175 - Response received from the model.
2025-10-02 10:12:03,863 - WARNING - types.py:5658 - Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
2025-10-02 10:12:05,299 - INFO - google_llm.py:122 - Sending out request, model: gemini-2.0-flash-exp, backend: GoogleLLMVariant.VERTEX_AI, stream: False
2025-10-02 10:12:05,300 - INFO - models.py:8185 - AFC is enabled with max remote calls: 10.
2025-10-02 10:12:08,704 - INFO - _client.py:1740 - HTTP Request: POST https://us-central1-aiplatform.googleapis.com/v1beta1/projects/contract-reader-2-dev/locations/us-central1/publishers/google/models/gemini-2.0-flash-exp:generateContent "HTTP/1.1 200 OK"
2025-10-02 10:12:08,705 - INFO - google_llm.py:175 - Response received from the model.
2025-10-02 10:12:08,706 - WARNING - types.py:5658 - Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
Creating new context cache for contract...
2025-10-02 10:12:12,910 - INFO - _client.py:1025 - HTTP Request: POST https://us-central1-aiplatform.googleapis.com/v1/projects/contract-reader-2-dev/locations/us-central1/cachedContents "HTTP/1.1 200 OK"
Cache created: projects/857991264119/locations/us-central1/cachedContents/1150326725884772352
Cached tokens: 5260
2025-10-02 10:12:12,912 - INFO - models.py:6458 - AFC is enabled with max remote calls: 10.
2025-10-02 10:12:41,351 - INFO - _client.py:1025 - HTTP Request: POST https://us-central1-aiplatform.googleapis.com/v1/projects/contract-reader-2-dev/locations/us-central1/publishers/google/models/gemini-2.5-pro:generateContent "HTTP/1.1 200 OK"
2025-10-02 10:12:42,521 - INFO - google_llm.py:122 - Sending out request, model: gemini-2.0-flash-exp, backend: GoogleLLMVariant.VERTEX_AI, stream: False
2025-10-02 10:12:42,522 - INFO - models.py:8185 - AFC is enabled with max remote calls: 10.
2025-10-02 10:12:46,125 - INFO - _client.py:1740 - HTTP Request: POST https://us-central1-aiplatform.googleapis.com/v1beta1/projects/contract-reader-2-dev/locations/us-central1/publishers/google/models/gemini-2.0-flash-exp:generateContent "HTTP/1.1 200 OK"
2025-10-02 10:12:46,127 - INFO - google_llm.py:175 - Response received from the model.
2025-10-02 10:12:46,127 - WARNING - types.py:5658 - Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
Attempting to reuse cache: projects/857991264119/locations/us-central1/cachedContents/1150326725884772352
2025-10-02 10:12:46,130 - INFO - models.py:6458 - AFC is enabled with max remote calls: 10.
2025-10-02 10:13:29,143 - INFO - _client.py:1025 - HTTP Request: POST https://us-central1-aiplatform.googleapis.com/v1/projects/contract-reader-2-dev/locations/us-central1/publishers/google/models/gemini-2.5-pro:generateContent "HTTP/1.1 200 OK"
2025-10-02 10:13:30,479 - INFO - google_llm.py:122 - Sending out request, model: gemini-2.0-flash-exp, backend: GoogleLLMVariant.VERTEX_AI, stream: False
2025-10-02 10:13:30,483 - INFO - models.py:8185 - AFC is enabled with max remote calls: 10.
2025-10-02 10:13:33,909 - INFO - _client.py:1740 - HTTP Request: POST https://us-central1-aiplatform.googleapis.com/v1beta1/projects/contract-reader-2-dev/locations/us-central1/publishers/google/models/gemini-2.0-flash-exp:generateContent "HTTP/1.1 200 OK"
2025-10-02 10:13:33,909 - INFO - google_llm.py:175 - Response received from the model.
2025-10-02 10:13:33,909 - WARNING - types.py:5658 - Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
Attempting to reuse cache: projects/857991264119/locations/us-central1/cachedContents/1150326725884772352
2025-10-02 10:13:33,909 - INFO - models.py:6458 - AFC is enabled with max remote calls: 10.
2025-10-02 10:14:22,664 - INFO - _client.py:1025 - HTTP Request: POST https://us-central1-aiplatform.googleapis.com/v1/projects/contract-reader-2-dev/locations/us-central1/publishers/google/models/gemini-2.5-pro:generateContent "HTTP/1.1 200 OK"
2025-10-02 10:14:24,189 - INFO - google_llm.py:122 - Sending out request, model: gemini-2.0-flash-exp, backend: GoogleLLMVariant.VERTEX_AI, stream: False
2025-10-02 10:14:24,190 - INFO - models.py:8185 - AFC is enabled with max remote calls: 10.
2025-10-02 10:14:27,643 - INFO - _client.py:1740 - HTTP Request: POST https://us-central1-aiplatform.googleapis.com/v1beta1/projects/contract-reader-2-dev/locations/us-central1/publishers/google/models/gemini-2.0-flash-exp:generateContent "HTTP/1.1 200 OK"
2025-10-02 10:14:27,644 - INFO - google_llm.py:175 - Response received from the model.
2025-10-02 10:14:27,646 - WARNING - types.py:5658 - Warning: there are non-text parts in the response: ['function_call'], returning concatenated text result from text parts. Check the full candidates.content.parts accessor to get the full model response.
Attempting to reuse cache: projects/857991264119/locations/us-central1/cachedContents/1150326725884772352
2025-10-02 10:14:27,648 - INFO - models.py:6458 - AFC is enabled with max remote calls: 10.
2025-10-02 10:14:47,381 - INFO - _client.py:1025 - HTTP Request: POST https://us-central1-aiplatform.googleapis.com/v1/projects/contract-reader-2-dev/locations/us-central1/publishers/google/models/gemini-2.5-pro:generateContent "HTTP/1.1 200 OK"
2025-10-02 10:14:48,792 - INFO - google_llm.py:122 - Sending out request, model: gemini-2.0-flash-exp, backend: GoogleLLMVariant.VERTEX_AI, stream: False
2025-10-02 10:14:48,793 - INFO - models.py:8185 - AFC is enabled with max remote calls: 10.
2025-10-02 10:14:54,099 - INFO - _client.py:1740 - HTTP Request: POST https://us-central1-aiplatform.googleapis.com/v1beta1/projects/contract-reader-2-dev/locations/us-central1/publishers/google/models/gemini-2.0-flash-exp:generateContent "HTTP/1.1 200 OK"
2025-10-02 10:14:54,100 - INFO - google_llm.py:175 - Response received from the model.
INFO:     127.0.0.1:58392 - "GET /apps/contract_reader_agent/users/user/sessions/5894fbb6-d907-4c20-bbd5-845d36d029dc HTTP/1.1" 200 OK
INFO:     127.0.0.1:53603 - "GET /debug/trace/session/5894fbb6-d907-4c20-bbd5-845d36d029dc HTTP/1.1" 200 OK