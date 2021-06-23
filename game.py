import sys
from itertools import chain, dropwhile, repeat
from random import randint, choice

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from enums import FieldItemState, GameStatus, GameDifficulty
from resources import Images, Sounds

from about import Ui_Dialog


class AboutDialog(QDialog, Ui_Dialog):
    def __init__(self, *args, **kwargs):
        super(AboutDialog, self).__init__(*args, **kwargs)
        self.setupUi(self)


class FieldItem(QPushButton):
    changed = pyqtSignal(QObject)
    rightButtonPressed = pyqtSignal()

    def __init__(self, y, x, *args, **kwargs):
        super(FieldItem, self).__init__(*args, **kwargs)
        self.y = y
        self.x = x
        self.status = FieldItemState.EMPTY

        self.has_mine = False
        self.visible = False
        self.neighbours = None
        self.blocked = False
        self.was_fatal_item = False

        self.current_image = self.parent().images.empty

        sizePolicy = QSizePolicy.Expanding
        policy = QSizePolicy()
        policy.setHorizontalPolicy(sizePolicy)
        policy.setVerticalPolicy(sizePolicy)
        policy.setWidthForHeight(True)
        self.setSizePolicy(policy)

        self.pressed.connect(lambda item=self: item.parent().item_clicked(item))
        self.rightButtonPressed.connect(self.toggle_status)
        self.parent().items_block_released.connect(self.release_block)

    def paintEvent(self, e: QPaintEvent):
        super().paintEvent(e)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawImage(
            self.rect().marginsAdded(QMargins() - 5),
            self.current_image
        )
        painter.end()

    def sizeHint(self):
        return QSize(45, 45)

    def minimumSizeHint(self):
        return QSize(self.sizeHint().width() // 2, self.sizeHint().height() // 2)

    def find_neighbours(self):
        if self.neighbours is None:
            parent = self.parent()
            y, x = self.y, self.x
            neighbours_coords = [(y + y0, x + x0) for x0 in (-1, 0, 1) for y0 in (-1, 0, 1)]
            neighbours_coords = list(filter(lambda c, height=parent.height, width=parent.width, y=y, x=x:
                                            0 <= c[0] < height and
                                            0 <= c[1] < width and
                                            c != (y, x),
                                            neighbours_coords
                                            )
                                     )

            neighbours = [parent.fieldItems2D[c[0]][c[1]] for c in neighbours_coords]
            self.neighbours = neighbours
            for neighbour in self.neighbours:
                neighbour.changed.connect(self.neighbour_was_changed)
        return self.neighbours

    def __str__(self):
        return f"Item ({self.y},{self.x})"

    def toggle_status(self):
        if not self.parent().game_run:
            return
        if self.status == FieldItemState.EMPTY and self.current_image != self.parent().images.empty:
            return

        # EMPTY -> MINE -> QUESTIONABLE -> EMPTY ... etc.
        self.status = list(dropwhile(lambda x, c=self.status: x != c, chain.from_iterable(repeat(FieldItemState, 2))))[
            1]

        self.parent().sounds.swap.play()

        if self.status == FieldItemState.MINE:
            self.current_image = self.parent().images.flag_red
            self.parent().mines_found_count(1)
        elif self.status == FieldItemState.QUESTIONABLE:
            self.current_image = self.parent().images.question
            self.parent().mines_found_count(-1)
        else:
            self.current_image = self.parent().images.empty
            self.blocked = False
            self.visible = False

        self.update()

    def show_any_state(self):
        self.visible = True
        parent = self.parent()

        neighbour_mines_count = sum(n.has_mine for n in self.neighbours)
        if neighbour_mines_count > 0 and not self.has_mine:
            self.current_image = parent.images.numbers[neighbour_mines_count]
        elif self.has_mine and self.was_fatal_item:
            self.current_image = parent.images.explosion
        elif self.has_mine:
            self.current_image = parent.images.mine
        else:
            self.current_image = parent.images.checked
        self.update()

    def calculate(self):
        if self.blocked:
            return
        self.blocked = True
        parent = self.parent()

        neighbour_mines_count = sum(n.has_mine for n in self.neighbours)
        self.visible = True
        if neighbour_mines_count > 0:
            self.current_image = parent.images.numbers[neighbour_mines_count]
        else:
            self.current_image = parent.images.checked
            self.changed.emit(self)

        self.update()

    def release_block(self):
        self.blocked = False

    def turn_visible(self):
        self.visible = True
        self.update()

    def neighbour_was_changed(self, neighbour):
        if neighbour.visible and not neighbour.has_mine:
            self.calculate()

    def reset(self):
        self.has_mine = False
        self.visible = False
        self.status = FieldItemState.EMPTY
        self.current_image = self.parent().images.empty
        self.was_fatal_item = False
        self.update()

    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.LeftButton:
            self.pressed.emit()
        elif e.button() == Qt.RightButton:
            self.rightButtonPressed.emit()
        else:
            pass


class GameField(QWidget):
    mines_count_changed = pyqtSignal(int)
    game_status_changed = pyqtSignal(GameStatus)
    game_started = pyqtSignal()
    game_ended = pyqtSignal()
    game_reset = pyqtSignal()
    items_block_released = pyqtSignal()

    def resizeEvent(self, e: QResizeEvent):
        w, h = e.size().width(), e.size().height()
        wh = min(w, h)
        new_size = QSize(wh, wh)
        e.accept()
        self.resize(new_size)

    def __init__(self, width=10, height=10, mines_count=10, *args, **kwargs):
        super(GameField, self).__init__(*args, **kwargs)

        self.images = self.parent().images
        self.sounds = self.parent().sounds

        self.width = width
        self.height = height
        self.mines_count = mines_count
        self.mines_found = 0

        self.fieldItems2D = []
        self.items_with_mines = []

        self.game_status = GameStatus.RUNNING
        self.game_run = False
        self.first_turn = True

        layout = QGridLayout(self)
        layout.setSpacing(0)
        layout.heightForWidth(True)

        for y in range(height):
            self.fieldItems2D.append([])
            for x in range(width):
                item = FieldItem(y, x, parent=self)
                self.fieldItems2D[y].append(item)
                layout.addWidget(item, y, x)

        self.fieldItems = list(chain.from_iterable(self.fieldItems2D))
        list(map(FieldItem.find_neighbours, self.fieldItems))

        self.game_ended.connect(self.stop_game)

        self.place_mines()

    def mines_found_count(self, change: int):
        self.mines_found += change
        self.mines_count_changed.emit(self.mines_found)

        # Check winning condition
        if self.mines_found == self.mines_count:
            mines_FieldItems_status = [i.status for i in self.items_with_mines]
            win_condition = set(mines_FieldItems_status) == {FieldItemState.MINE}
            if win_condition:
                self.win()

    def place_mines(self):
        mines_positions = set()
        total_field_positions = self.width * self.height
        while len(mines_positions) < self.mines_count:
            mines_positions.add(randint(0, total_field_positions - 1))

        self.items_with_mines = []
        for i, mines_position in enumerate(mines_positions):
            y, x = mines_position // self.width, mines_position % self.height
            # print(f"#{i} - {mines_position}([{y},{x}])")
            self.items_with_mines.append(self.fieldItems2D[y][x])
            self.fieldItems2D[y][x].has_mine = True
            self.fieldItems2D[y][x].update()

    def item_clicked(self, item: FieldItem):
        if self.game_run:
            if item.status != FieldItemState.EMPTY:
                return
            if item.has_mine and self.first_turn:
                self.sounds.pop.play()
                item.has_mine = False
                found_new_mine_spot = False
                while not found_new_mine_spot:
                    current_item = choice(self.fieldItems)
                    if not current_item.has_mine:
                        # print(f"Ha-ha, found mine on first turn! Ok, that mine was moved to {current_item}")
                        index = self.items_with_mines.index(item)
                        self.items_with_mines[index] = current_item
                        current_item.has_mine = True
                        found_new_mine_spot = True
                item.calculate()

            elif item.has_mine:
                item.was_fatal_item = True
                self.sounds.blow.play()
                item.update()
                self.loose()
            elif item.visible:
                pass
            else:
                self.sounds.pop.play()
                item.calculate()

            item.update()
            self.items_block_released.emit()
            self.first_turn = False

        elif self.game_status == GameStatus.RUNNING:
            self.first_turn = False
            self.start_game()
            self.item_clicked(item)

    def win(self):
        self.game_status = GameStatus.WON
        self.sounds.win.play()
        # print("You have won!")
        self.stop_game()
        self.game_ended.emit()
        self.game_status_changed.emit(self.game_status)

    def loose(self):
        self.game_status = GameStatus.LOST
        # print("You loose!")
        self.game_run = False
        self.game_ended.emit()
        self.game_status_changed.emit(self.game_status)

    def start_game(self):
        self.game_reset.emit()
        self.game_status = GameStatus.RUNNING
        self.game_run = True
        self.first_turn = True
        self.game_started.emit()

    def stop_game(self):
        self.game_run = False
        list(map(FieldItem.show_any_state, self.fieldItems))
        self.timer = QTimer(self)
        self.timer.singleShot(3000, self.reset_game)

    def reset_game(self):
        try:
            del self.timer
        except Exception:
            pass
        list(map(FieldItem.reset, self.fieldItems))
        self.mines_found = 0
        self.game_run = False
        self.game_status = GameStatus.RUNNING
        list(map(FieldItem.reset, self.fieldItems))
        self.place_mines()
        self.game_status_changed.emit(self.game_status)
        self.game_reset.emit()


class StatusBar(QWidget):
    def __init__(self, *args, **kwargs):
        super(StatusBar, self).__init__(*args, **kwargs)
        self.images = self.parent().images

        layout = QHBoxLayout()
        self.setLayout(layout)

        self.mines_counter = QLCDNumber(self)
        self.mines_counter.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self.mines_counter, alignment=Qt.AlignLeft)

        self.img = QLabel(self)
        self.pixmaps = {"smile": QPixmap().fromImage(self.images.smile, Qt.AutoColor),
                        "dead": QPixmap().fromImage(self.images.dead, Qt.AutoColor),
                        "won": QPixmap().fromImage(self.images.win_smile, Qt.AutoColor)}
        self.set_smile(GameStatus.RUNNING)

        self.img.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.img)

        self.timer_counter = QLCDNumber(self)
        self.timer_counter.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self.timer_counter, alignment=Qt.AlignRight)
        self.timer = QTimer(self)

    def set_smile(self, game_status: GameStatus):
        if game_status == GameStatus.RUNNING:
            self.img.setPixmap(self.pixmaps["smile"])
        elif game_status == GameStatus.WON:
            self.img.setPixmap(self.pixmaps["won"])
        elif game_status == GameStatus.LOST:
            self.img.setPixmap(self.pixmaps["dead"])
        self.img.update()

    def start_timer(self):
        self.end_timer()
        self.timer = QTimer(self)
        self.timer_counter.display(0)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(lambda x=self.timer_counter: x.display(x.value() + 1))
        self.timer.start()

    def end_timer(self):
        try:
            self.timer.stop()
            self.timer.disconnect()
            del self.timer
        except Exception:
            pass

    def update_counter(self, value):
        self.mines_counter.display(value)

    def reset(self):
        self.timer_counter.display(0)
        self.mines_counter.display(0)

    # def sizeHint(self):
    #     return QSize(40, 60)


class GameActions(QObject):
    def __init__(self, *args, **kwargs):
        super(GameActions, self).__init__(*args, **kwargs)
        images = self.parent().images

        self.reset = QAction(QIcon(QPixmap.fromImage(images.restart)), "Restart", self)

        self.difficulty = QActionGroup(self)
        self.easy = QAction(QIcon(QPixmap.fromImage(images.easy)), "Easy", self)
        self.difficulty.addAction(self.easy)

        self.medium = QAction(QIcon(QPixmap.fromImage(images.medium)), "Medium", self)
        self.difficulty.addAction(self.medium)

        self.hard = QAction(QIcon(QPixmap.fromImage(images.hard)), "Hard", self)
        self.difficulty.addAction(self.hard)
        [a.setCheckable(True) for a in self.difficulty.actions()]
        self.easy.setChecked(True)

        self.toggleSound = QAction("Sounds", self)
        self.toggleSound.setIcon(QIcon(QPixmap.fromImage(images.audio_on)))
        self.toggleSound.setCheckable(True)
        self.toggleSound.setChecked(True)

        self.exit = QAction(QIcon(QPixmap.fromImage(images.close)), "Exit", self)

        self.aboutDialog = QAction(QIcon(QPixmap.fromImage(images.about)), "About", self)

    def bind(self):
        parent = self.parent()
        self.exit.triggered.connect(parent.close)
        self.reset.triggered.connect(parent.game_field.reset_game)
        self.toggleSound.triggered.connect(parent.sounds.toggle_sound)
        self.toggleSound.triggered.connect(self.change_sound_icon)
        self.easy.triggered.connect(lambda p=parent: parent.set_difficulty(GameDifficulty.EASY))
        self.medium.triggered.connect(lambda p=parent: parent.set_difficulty(GameDifficulty.MEDIUM))
        self.hard.triggered.connect(lambda p=parent: parent.set_difficulty(GameDifficulty.HARD))
        self.aboutDialog.triggered.connect(parent.show_about_dialog)

    def change_sound_icon(self, val):
        if val:
            self.toggleSound.setIcon(QIcon(QPixmap.fromImage(self.parent().images.audio_on)))
        else:
            self.toggleSound.setIcon(QIcon(QPixmap.fromImage(self.parent().images.audio_off)))


class GameMenu(QObject):
    def __init__(self, *args, **kwargs):
        super(GameMenu, self).__init__(*args, **kwargs)
        parent = self.parent()
        actions = parent.game_actions

        parent_menu = self.parent().menuBar().addMenu("&File")
        parent_menu.addAction(actions.reset)

        parent_menu.addAction(actions.toggleSound)

        difficulty_menu = parent_menu.addMenu("&Difficulty")
        difficulty_menu.addActions(actions.difficulty.actions())

        parent_menu.addMenu(difficulty_menu)
        parent_menu.addAction(actions.exit)

        help_menu = self.parent().menuBar().addMenu("&Help")
        about = actions.aboutDialog
        help_menu.addAction(about)


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.images = Images()
        self.sounds = Sounds()
        self.setWindowIcon(QIcon(QPixmap.fromImage(self.images.dynamite)))
        self.setWindowTitle("Mine Reaper")
        self.game_actions = GameActions(self)
        self.menu = GameMenu(self)
        self.difficulty = GameDifficulty.EASY

        self.initialize()

    def initialize(self):
        self.mainWidget = QWidget(self)

        height, width, mines_count = self.difficulty.value
        self.game_field = GameField(height=height, width=width, mines_count=mines_count, parent=self)

        layout = QVBoxLayout(self.mainWidget)
        self.mainWidget.setLayout(layout)
        self.status_bar = StatusBar(self)
        layout.addWidget(self.status_bar)

        self.game_actions.bind()

        layout.addWidget(self.game_field)

        self.game_field.mines_count_changed.connect(self.status_bar.mines_counter.display)
        self.game_field.game_started.connect(self.status_bar.start_timer)
        self.game_field.game_ended.connect(self.status_bar.end_timer)
        self.game_field.game_reset.connect(self.status_bar.reset)
        self.game_field.game_status_changed.connect(self.status_bar.set_smile)

        self.setCentralWidget(self.mainWidget)
        self.mainWidget.resize = self.game_field.resize
        self.resize = self.game_field.resize
        self.show()

    def set_difficulty(self, difficulty: GameDifficulty = GameDifficulty.EASY):
        self.difficulty = difficulty
        self.layout().removeWidget(self.mainWidget)
        self.mainWidget.setParent(None)
        self.initialize()

    def show_about_dialog(self):
        self.about_dialog = AboutDialog(self)
        self.about_dialog.exec_()


app = QApplication(sys.argv)
window = MainWindow()

app.exec_()
