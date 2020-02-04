from threading import Lock


active_provisioning = Lock()
provisioning_pid = None
