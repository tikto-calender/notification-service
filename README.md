# TikTo Notification Service

Small Python HTTP service that stores notification records in memory. Backend uses it to check notification health and send a test notification to the service log.

## Run locally

Use Python 3.11 or later. The server uses the Python standard library.

**Linux/macOS**

```sh
python3 main.py
```

**Windows PowerShell**

```powershell
python main.py
```

Open [http://localhost:8000/health](http://localhost:8000/health) to check the version. For a full demo, point [Backend](https://github.com/tikto-calender/backend) to `http://localhost:8000` and select **Test notification** in the Frontend. The response uses channel `LOG` and the test appears in the service terminal.

Run the tests with `python3 -m unittest discover -s test -v` on Linux/macOS or `python -m unittest discover -s test -v` on Windows.

## Deployment

Push to `dev` to build the GHCR image and update Manifest. After checking Dev, run [Promote Notification](https://github.com/tikto-calender/manifest#promote-to-production) and verify Prod before running **Finalize release**.
