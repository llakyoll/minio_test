import os
from server_arch.apiSender.report_manager import ReportManager

reporter = ReportManager()

reporter.set_api_credentials(
    gateway_base=os.environ.get("GATEWAY_BASE", "http://localhost:8085"),
    api_key=os.environ.get("API_KEY", "test-key-123"),
    branch_id=os.environ.get("BRANCH_ID")
)

reporter.add_alarm(
    name="test_alarm",
    cooldown_seconds=5
)

reporter.send_alarm("test_alarm", data={"mesaj": "Docker ortamı çalışıyor"})
