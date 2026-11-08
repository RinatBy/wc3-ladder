import tempfile
import unittest
from pathlib import Path
import core
import controller


class CommandsTests(unittest.TestCase):
    def test_regular_user_can_host_but_not_send_worker_admin_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = core.Store(Path(tmp)/'state.db',['HostMap1'])
            store.add_map('a'*64,'w3x','Echo Isles')
            bot = controller.Commands(store, lambda: {'HostMap1':dict(time=1000,busy=False)})
            result = bot.handle('Player2','!host aaaaaaaaaaaa Friends',now=1000)
            self.assertEqual(result[0],('HostMap1','!hmhost 1000 aaaaaaaaaaaa Player2 Friends'))
            self.assertEqual(bot.handle('Player2','!quit',now=1003)[0][0],'Player2')
            self.assertNotIn('!quit',str(bot.handle('Player3','!say /w HostMap1 !quit',now=1003)))

    def test_upload_disabled_without_https_and_bot_messages_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = core.Store(Path(tmp)/'state.db',['HostMap1'])
            bot = controller.Commands(store,lambda: {})
            self.assertEqual(bot.handle('HostMap1','!host x room',now=1000),[])
            result = bot.handle('uPlay','!upload',now=1000)
            self.assertNotIn('http',str(result))
            self.assertIn('not enabled',result[0][1])


if __name__ == '__main__':
    unittest.main()
