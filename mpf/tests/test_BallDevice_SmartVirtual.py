from mpf.tests.MpfGameTestCase import MpfGameTestCase
from mpf.tests.MpfTestCase import test_config


class TestBallDeviceSmartVirtual(MpfGameTestCase):
    def get_config_file(self):
        return 'test_ball_device.yaml'

    def get_machine_path(self):
        return 'tests/machine_files/ball_device/'

    def get_platform(self):
        return 'smart_virtual'

    def test_eject(self):
        # add initial balls to trough
        self.hit_switch_and_run("s_ball_switch1", 1)
        self.hit_switch_and_run("s_ball_switch2", 1)
        self.assertEqual(2, self.machine.ball_devices["test_trough"].balls)
        self.assertEqual(2, self.machine.ball_devices["test_trough"].available_balls)

        # call eject
        self.machine.ball_devices["test_trough"].eject()
        self.assertEqual(2, self.machine.ball_devices["test_trough"].balls)
        self.assertEqual(1, self.machine.ball_devices["test_trough"].available_balls)

        # one ball should be gone
        self.advance_time_and_run(30)
        self.assertEqual(1, self.machine.ball_devices["test_trough"].balls)
        self.assertEqual(1, self.machine.ball_devices["test_trough"].available_balls)

    def test_eject_all(self):
        # add initial balls to trough
        self.hit_switch_and_run("s_ball_switch1", 1)
        self.hit_switch_and_run("s_ball_switch2", 1)
        self.assertEqual(2, self.machine.ball_devices["test_trough"].balls)
        self.assertEqual(2, self.machine.ball_devices["test_trough"].available_balls)

        # call eject_all
        self.machine.ball_devices["test_trough"].eject_all()
        self.advance_time_and_run(30)

        # all balls should be gone
        self.assertEqual(0, self.machine.ball_devices["test_trough"].balls)
        self.assertEqual(0, self.machine.ball_devices["test_trough"].available_balls)

    @test_config("test_player_controlled_eject.yaml")
    def test_player_controlled_eject(self):
        self.start_game()
        self.advance_time_and_run(10)
        self.assertBallsInPlay(1)
        self.assertBallsOnPlayfield(0)

        self.hit_and_release_switch("s_launch_button")
        self.advance_time_and_run(5)
        self.assertBallsOnPlayfield(1)
