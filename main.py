from server_arch.apiSender.report_manager import ReportManager

reporter = ReportManager()


reporter.set_api_credentials()

reporter.send_alarm()

