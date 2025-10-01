(venv) C:\Users\bencl\Proyectos\cr2.0\backend\agentic>adk web
C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\cli\fast_api.py:177: UserWarning: [EXPERIMENTAL] InMemoryCredentialService: This feature is experimental and may change or be removed in future versions without notice. It may introduce breaking changes at any time.
  credential_service = InMemoryCredentialService()
C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\auth\credential_service\in_memory_credential_service.py:33: UserWarning: [EXPERIMENTAL] BaseCredentialService: This feature is experimental and may change or be removed in future versions without notice. It may introduce breaking changes at any time.
  super().__init__()
INFO:     Started server process [40444]
INFO:     Waiting for application startup.

+-----------------------------------------------------------------------------+
| ADK Web Server started                                                      |
|                                                                             |
| For local testing, access at http://127.0.0.1:8000.                         |
+-----------------------------------------------------------------------------+

INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:57272 - "GET / HTTP/1.1" 307 Temporary Redirect
INFO:     127.0.0.1:57272 - "GET /dev-ui/ HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:57272 - "GET /dev-ui/chunk-EQDQRRRY.js HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:57272 - "GET /dev-ui/polyfills-B6TNHZQ6.js HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:63730 - "GET /dev-ui/main-W7QZBYAR.js HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:62210 - "GET /dev-ui/styles-4VDSPQ37.css HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:62210 - "GET /dev-ui/assets/config/runtime-config.json HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:62210 - "GET /dev-ui/assets/ADK-512-color.svg HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:62210 - "GET /list-apps?relative_path=./ HTTP/1.1" 200 OK
INFO:     127.0.0.1:62210 - "POST /apps/contract_reader_agent/users/user/sessions HTTP/1.1" 200 OK
INFO:     127.0.0.1:62210 - "GET /apps/contract_reader_agent/eval_sets HTTP/1.1" 200 OK
INFO:     127.0.0.1:63730 - "GET /apps/contract_reader_agent/eval_results HTTP/1.1" 200 OK
INFO:     127.0.0.1:63730 - "GET /apps/contract_reader_agent/users/user/sessions HTTP/1.1" 200 OK
INFO:     127.0.0.1:63730 - "GET /apps/contract_reader_agent/users/user/sessions HTTP/1.1" 200 OK
INFO:     127.0.0.1:55503 - "POST /run_sse HTTP/1.1" 200 OK
2025-10-01 16:43:20,022 - INFO - envs.py:47 - Loaded .env file for contract_reader_agent at C:\Users\bencl\Proyectos\cr2.0\backend\.env
2025-10-01 16:43:20,023 - INFO - envs.py:47 - Loaded .env file for contract_reader_agent at C:\Users\bencl\Proyectos\cr2.0\backend\.env
2025-10-01 16:43:20,055 - INFO - agent_loader.py:126 - Found root_agent in contract_reader_agent.agent
C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\cli\adk_web_server.py:450: UserWarning: [EXPERIMENTAL] App: This feature is experimental and may change or be removed in future versions without notice. It may introduce breaking changes at any time.
  agentic_app = App(
2025-10-01 16:43:21,662 - INFO - google_llm.py:122 - Sending out request, model: gemini-2.0-flash-exp, backend: GoogleLLMVariant.VERTEX_AI, stream: False
2025-10-01 16:43:21,663 - INFO - models.py:8185 - AFC is enabled with max remote calls: 10.
2025-10-01 16:43:25,585 - INFO - _client.py:1740 - HTTP Request: POST https://us-east5-aiplatform.googleapis.com/v1beta1/projects/contract-reader-2-dev/locations/us-east5/publishers/google/models/gemini-2.0-flash-exp:generateContent "HTTP/1.1 404 Not Found"
2025-10-01 16:43:25,725 - ERROR - adk_web_server.py:1284 - Error in event_generator: 404 NOT_FOUND. {'error': {'code': 404, 'message': 'Publisher Model `projects/contract-reader-2-dev/locations/us-east5/publishers/google/models/gemini-2.0-flash-exp` not found.', 'status': 'NOT_FOUND'}}
Traceback (most recent call last):
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\cli\adk_web_server.py", line 1274, in event_generator
    async for event in agen:
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\runners.py", line 332, in run_async
    async for event in agen:
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\runners.py", line 328, in _run_with_trace
    async for event in agen:
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\runners.py", line 383, in _exec_with_plugin
    async for event in agen:
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\runners.py", line 317, in execute
    async for event in agen:
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\agents\base_agent.py", line 248, in run_async
    async for event in agen:
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\agents\base_agent.py", line 238, in _run_with_trace
    async for event in agen:
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\agents\llm_agent.py", line 341, in _run_async_impl
    async for event in agen:
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\flows\llm_flows\base_llm_flow.py", line 355, in run_async
    async for event in agen:
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\flows\llm_flows\base_llm_flow.py", line 391, in _run_one_step_async
    async for llm_response in agen:
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\flows\llm_flows\base_llm_flow.py", line 749, in _call_llm_async
    async for event in agen:
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\flows\llm_flows\base_llm_flow.py", line 733, in _call_llm_with_tracing
    async for llm_response in agen:
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\flows\llm_flows\base_llm_flow.py", line 922, in _run_and_handle_error
    raise model_error
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\flows\llm_flows\base_llm_flow.py", line 906, in _run_and_handle_error
    async for response in agen:
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\models\google_llm.py", line 170, in generate_content_async
    response = await self.api_client.aio.models.generate_content(
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\genai\models.py", line 8191, in generate_content
    response = await self._generate_content(
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\genai\models.py", line 7026, in _generate_content
    response = await self._api_client.async_request(
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\genai\_api_client.py", line 1325, in async_request
    result = await self._async_request(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\genai\_api_client.py", line 1270, in _async_request
    return await self._async_retry(  # type: ignore[no-any-return]
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\tenacity\asyncio\__init__.py", line 111, in __call__
    do = await self.iter(retry_state=retry_state)
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\tenacity\asyncio\__init__.py", line 153, in iter
    result = await action(retry_state)
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\tenacity\_utils.py", line 99, in inner
    return call(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\tenacity\__init__.py", line 418, in exc_check
    raise retry_exc.reraise()
          ^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\tenacity\__init__.py", line 185, in reraise
    raise self.last_attempt.result()
          ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bencl\AppData\Local\Programs\Python\Python311\Lib\concurrent\futures\_base.py", line 449, in result
    return self.__get_result()
           ^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bencl\AppData\Local\Programs\Python\Python311\Lib\concurrent\futures\_base.py", line 401, in __get_result
    raise self._exception
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\tenacity\asyncio\__init__.py", line 114, in __call__
    result = await fn(*args, **kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\genai\_api_client.py", line 1250, in _async_request_once
    await errors.APIError.raise_for_async_response(client_response)
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\genai\errors.py", line 159, in raise_for_async_response
    raise ClientError(status_code, response_json, response)
google.genai.errors.ClientError: 404 NOT_FOUND. {'error': {'code': 404, 'message': 'Publisher Model `projects/contract-reader-2-dev/locations/us-east5/publishers/google/models/gemini-2.0-flash-exp` not found.', 'status': 'NOT_FOUND'}}
INFO:     127.0.0.1:55503 - "GET /apps/contract_reader_agent/users/user/sessions/a42c08a2-018e-49d7-82ba-4307f6ace12d HTTP/1.1" 200 OK
INFO:     127.0.0.1:62760 - "GET /debug/trace/session/a42c08a2-018e-49d7-82ba-4307f6ace12d HTTP/1.1" 200 OK