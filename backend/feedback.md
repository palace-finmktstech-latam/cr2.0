(venv) C:\Users\bencl\Proyectos\cr2.0\backend>adk run agentic/contract_reader_agent
Log setup complete: C:\Users\bencl\AppData\Local\Temp\agents_log\agent.20251002_145146.log
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Scripts\adk.exe\__main__.py", line 7, in <module>
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\click\core.py", line 1462, in __call__
    return self.main(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\click\core.py", line 1383, in main
    rv = self.invoke(ctx)
         ^^^^^^^^^^^^^^^^
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\click\core.py", line 1850, in invoke
    return _process_result(sub_ctx.command.invoke(sub_ctx))
                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\click\core.py", line 1246, in invoke
    return ctx.invoke(self.callback, **ctx.params)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\click\core.py", line 814, in invoke
    return callback(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\cli\cli_tools_click.py", line 419, in cli_run
    logs.log_to_tmp_folder()
  File "C:\Users\bencl\Proyectos\cr2.0\backend\venv\Lib\site-packages\google\adk\cli\utils\logs.py", line 72, in log_to_tmp_folder
    os.symlink(log_filepath, latest_log_link)
OSError: [WinError 1314] A required privilege is not held by the client: 'C:\\Users\\bencl\\AppData\\Local\\Temp\\agents_log\\agent.20251002_145146.log' -> 'C:\\Users\\bencl\\AppData\\Local\\Temp\\agents_log\\agent.latest.log'