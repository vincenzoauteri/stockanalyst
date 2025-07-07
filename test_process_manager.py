import unittest
import time
import os
import sys
from pathlib import Path
import psutil
from process_manager import EnhancedProcessManager
from webapp_manager import check_port_available, APP_PORT, WEBAPP_NAME, APP_COMMAND

class TestEnhancedProcessManager(unittest.TestCase):
    def setUp(self):
        """Set up for each test."""
        self.test_name = "test_app"
        self.pid_file = Path(f"/tmp/{self.test_name}.pid")
        self.status_file = Path(f"/tmp/{self.test_name}_status.json")
        # Use a simple command that runs in the background
        self.command = [sys.executable, "-c", "import time; time.sleep(10)"]
        
        self.pm = EnhancedProcessManager(
            name=self.test_name,
            pid_file=self.pid_file,
            status_file=self.status_file,
            command=self.command,
            working_dir=os.getcwd()
        )
        # Clean up before each test
        self.pm.stop()

    def tearDown(self):
        """Clean up after each test."""
        self.pm.stop()

    def test_01_start_and_is_running(self):
        """Test starting the process and checking if it's running."""
        print("\n--- Testing Start and is_running ---")
        self.assertFalse(self.pm.is_running(), "Process should not be running initially.")
        
        success = self.pm.start()
        self.assertTrue(success, "Process should start successfully.")
        time.sleep(1)  # Give it a moment to start
        
        self.assertTrue(self.pm.is_running(), "Process should be running after start.")
        
        pid = self.pm.get_pid()
        self.assertIsNotNone(pid, "PID should not be None.")
        self.assertTrue(psutil.pid_exists(pid), f"PID {pid} should exist.")

    def test_02_stop(self):
        """Test stopping the process."""
        print("\n--- Testing Stop ---")
        self.pm.start()
        time.sleep(1)
        self.assertTrue(self.pm.is_running(), "Process should be running before stop.")
        
        success = self.pm.stop()
        self.assertTrue(success, "Process should stop successfully.")
        time.sleep(1) # Give it a moment to stop
        
        self.assertFalse(self.pm.is_running(), "Process should not be running after stop.")
        self.assertFalse(self.pid_file.exists(), "PID file should be cleaned up.")
        self.assertFalse(self.status_file.exists(), "Status file should be cleaned up.")

    def test_03_restart(self):
        """Test restarting the process."""
        print("\n--- Testing Restart ---")
        self.pm.start()
        time.sleep(1)
        initial_pid = self.pm.get_pid()
        self.assertTrue(self.pm.is_running(), "Process should be running before restart.")
        
        success = self.pm.restart()
        self.assertTrue(success, "Process should restart successfully.")
        time.sleep(1)
        
        self.assertTrue(self.pm.is_running(), "Process should be running after restart.")
        new_pid = self.pm.get_pid()
        self.assertIsNotNone(new_pid, "New PID should not be None.")
        self.assertNotEqual(initial_pid, new_pid, "PID should change after restart.")

    def test_04_status(self):
        """Test the status functionality."""
        print("\n--- Testing Status ---")
        # Status when stopped
        status_stopped = self.pm.get_status()
        self.assertFalse(status_stopped['running'])
        self.assertEqual(status_stopped['status'], 'stopped')

        # Status when running
        self.pm.start()
        time.sleep(1)
        status_running = self.pm.get_status()
        self.assertTrue(status_running['running'])
        self.assertEqual(status_running['status'], 'running')
        self.assertIsNotNone(status_running['pid'])

class TestWebAppManagerFunctions(unittest.TestCase):
    def setUp(self):
        """Set up for webapp manager tests."""
        self.webapp_service = EnhancedProcessManager(
            name=WEBAPP_NAME,
            pid_file=Path(f"/tmp/{WEBAPP_NAME}.pid"),
            status_file=Path(f"/tmp/{WEBAPP_NAME}_status.json"),
            command=APP_COMMAND,
            working_dir='/app'
        )
        # Ensure the webapp is stopped before each test
        self.webapp_service.stop()

    def tearDown(self):
        """Clean up after webapp manager tests."""
        self.webapp_service.stop()

    def test_check_port_available(self):
        """Test the port availability check."""
        print("\n--- Testing Port Availability ---")
        # Assuming the port is free initially
        self.assertTrue(check_port_available(APP_PORT), f"Port {APP_PORT} should be available.")
        
        # Cannot easily test the 'in-use' case without starting a real server,
        # which is what the main tests do. This is a basic sanity check.

if __name__ == '__main__':
    # Run tests in a specific order
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestEnhancedProcessManager))
    suite.addTest(unittest.makeSuite(TestWebAppManagerFunctions))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with a status code indicating success or failure
    if result.wasSuccessful():
        print("\nAll tests passed successfully!")
        sys.exit(0)
    else:
        print("\nSome tests failed.")
        sys.exit(1)
