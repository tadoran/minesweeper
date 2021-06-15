from PyQt5.QtCore import QObject
from PyQt5.QtGui import QImage


class Images(QObject):
    def __init__(self):
        self.empty = QImage()
        self.checked = QImage("img//checked.png")
        self.clock = QImage("img//clock.png")
        self.dead = QImage("img//dead.png")
        self.explosion = QImage("img//explosion.png")
        self.flag_green = QImage("img//flag_green.png")
        self.flag_red = QImage("img//flag_red.png")
        self.mine = QImage("img//mine.png")
        self.question = QImage("img//question.png")
        self.smile = QImage("img//smile.png")
        self.win_smile = QImage("img//win_smile.png")
        self.easy = QImage("img//easy.png")
        self.medium = QImage("img//medium.png")
        self.hard = QImage("img//hard.png")
        self.restart = QImage("img//restart.png")
        self.close = QImage("img//close.png")
        self.dynamite = QImage("img//dynamite.png")
        self.about = QImage("img//about.png")
        self.audio_on = QImage("img//audio_on.png")
        self.audio_off = QImage("img//audio_off.png")

        self.numbers = [
            QImage(),
            QImage("img//1.png"),
            QImage("img//2.png"),
            QImage("img//3.png"),
            QImage("img//4.png"),
            QImage("img//5.png"),
            QImage("img//6.png"),
            QImage("img//7.png"),
            QImage("img//8.png"),
            QImage("img//9.png")
        ]


class Sounds(QObject):
    def __init__(self, audio_on=True, *args, **kwargs):
        super(Sounds, self).__init__(*args, **kwargs)
        self.audio_on = audio_on
        self.pop = GameSound("wav//pop.wav", self)
        self.win = GameSound("wav//win.wav", self)
        self.blow = GameSound("wav//blow.wav", self)
        self.swap = GameSound("wav//swap.wav", self)

    def play(self):
        if self.parent.audio_on:
            super(Sounds, self).play()

    def toggle_sound(self, toggle: bool):
        print(toggle)
        self.audio_on = toggle

class GameSound(QSound):
    def __init__(self, filename, parent):
        super(GameSound, self).__init__(filename)
        self.parent = parent

    def play(self):
        if self.parent.audio_on:
            super(GameSound, self).play()
