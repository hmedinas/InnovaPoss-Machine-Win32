from unittest import TestCase

from src.innovapos import TCPDataAdapter


class TestTCPDataAdapter(TestCase):
    _hostname_: str = "127.0.0.1"
    _port_: str = "3000"
    adapter: TCPDataAdapter

    def test_open_adapter_for_emulator(self):
        self.adapter.open({"host": self._hostname_, "port": self._port_})

    def test_msg_get_status(self):
        self.adapter.open({"host": self._hostname_, "port": self._port_})
        self.adapter.send_message("just hello")
        reply = self.adapter.transact_message("CCM_Getstatus")
        self.assertEqual("CCM_STATUS_OK", reply, "CCM result was not as expected")

    @classmethod
    def setUpClass(cls):
        cls.adapter = TCPDataAdapter()

    def tearDown(self):
        self.adapter.close()

