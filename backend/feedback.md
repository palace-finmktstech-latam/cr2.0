(venv) C:\Users\bencl\Proyectos\cr2.0\backend\agentic>adk web
C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\cli\fast_api.py:177: UserWarning: [EXPERIMENTAL] InMemoryCredentialService: This feature is experimental and may change or be removed in future versions without notice. It may introduce breaking changes at any time.
  credential_service = InMemoryCredentialService()
C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\auth\credential_service\in_memory_credential_service.py:33: UserWarning: [EXPERIMENTAL] BaseCredentialService: This feature is experimental and may change or be removed in future versions without notice. It may introduce breaking changes at any time.
  super().__init__()
INFO:     Started server process [56064]
INFO:     Waiting for application startup.

+-----------------------------------------------------------------------------+
| ADK Web Server started                                                      |
|                                                                             |
| For local testing, access at http://127.0.0.1:8000.                         |
+-----------------------------------------------------------------------------+

INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:52539 - "GET / HTTP/1.1" 307 Temporary Redirect
INFO:     127.0.0.1:52539 - "GET /dev-ui/ HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:52539 - "GET /dev-ui/chunk-EQDQRRRY.js HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:52539 - "GET /dev-ui/polyfills-B6TNHZQ6.js HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:54386 - "GET /dev-ui/styles-4VDSPQ37.css HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:59730 - "GET /dev-ui/main-W7QZBYAR.js HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:59730 - "GET /dev-ui/assets/config/runtime-config.json HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:59730 - "GET /dev-ui/assets/ADK-512-color.svg HTTP/1.1" 304 Not Modified
INFO:     127.0.0.1:59730 - "GET /list-apps?relative_path=./ HTTP/1.1" 200 OK
INFO:     127.0.0.1:59730 - "POST /apps/contract_reader_agent/users/user/sessions HTTP/1.1" 200 OK
INFO:     127.0.0.1:59730 - "GET /apps/contract_reader_agent/eval_sets HTTP/1.1" 200 OK
INFO:     127.0.0.1:54386 - "GET /apps/contract_reader_agent/eval_results HTTP/1.1" 200 OK
INFO:     127.0.0.1:54386 - "GET /apps/contract_reader_agent/users/user/sessions HTTP/1.1" 200 OK
INFO:     127.0.0.1:54386 - "GET /apps/contract_reader_agent/users/user/sessions HTTP/1.1" 200 OK
INFO:     127.0.0.1:64529 - "POST /run_sse HTTP/1.1" 200 OK
2025-10-02 09:01:03,634 - INFO - envs.py:47 - Loaded .env file for contract_reader_agent at C:\Users\bencl\Proyectos\cr2.0\backend\.env
2025-10-02 09:01:03,635 - INFO - envs.py:47 - Loaded .env file for contract_reader_agent at C:\Users\bencl\Proyectos\cr2.0\backend\.env
2025-10-02 09:01:03,651 - ERROR - adk_web_server.py:1284 - Error in event_generator: Fail to load 'contract_reader_agent.agent' module. closing parenthesis ')' does not match opening parenthesis '[' on line 303 (agent.py, line 309)
Traceback (most recent call last):
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\cli\adk_web_server.py", line 1264, in event_generator
    runner = await self.get_runner_async(req.app_name)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\cli\adk_web_server.py", line 444, in get_runner_async
    agent_or_app = self.agent_loader.load_agent(app_name)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\cli\utils\agent_loader.py", line 234, in load_agent
    agent_or_app = self._perform_load(agent_name)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\cli\utils\agent_loader.py", line 210, in _perform_load
    if root_agent := self._load_from_submodule(actual_agent_name):
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\cli\utils\agent_loader.py", line 151, in _load_from_submodule
    raise e
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\cli\utils\agent_loader.py", line 118, in _load_from_submodule
    module_candidate = importlib.import_module(f"{agent_name}.agent")
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bencl\AppData\Local\Programs\Python\Python311\Lib\importlib\__init__.py", line 126, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1204, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1176, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1147, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 690, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 936, in exec_module
  File "<frozen importlib._bootstrap_external>", line 1074, in get_code
  File "<frozen importlib._bootstrap_external>", line 1004, in source_to_code
  File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
  File "C:\Users\bencl\Proyectos\cr2.0\backend\agentic\contract_reader_agent\agent.py", line 309
    )
    ^
SyntaxError: Fail to load 'contract_reader_agent.agent' module. closing parenthesis ')' does not match opening parenthesis '[' on line 303
INFO:     127.0.0.1:64529 - "GET /apps/contract_reader_agent/users/user/sessions/c551424a-cec5-43ab-b5b0-fdc620a6d746 HTTP/1.1" 200 OK
INFO:     127.0.0.1:57054 - "GET /debug/trace/session/c551424a-cec5-43ab-b5b0-fdc620a6d746 HTTP/1.1" 200 OK