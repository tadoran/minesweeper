import sys
from enum import Enum
from itertools import chain, dropwhile, repeat
from random import randint, choice

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *


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


class FieldState(Enum):
    EMPTY = 0
    MINE = 1
    QUESTIONABLE = 2


class FieldItemVisibility:
    hidden = 0
    visible = 1


class FieldItem(QPushButton):
    changed = pyqtSignal(QObject)
    rightButtonPressed = pyqtSignal()

    def __init__(self, y, x, *args, **kwargs):
        super(FieldItem, self).__init__(*args, **kwargs)
        self.y = y
        self.x = x
        self.status = FieldState.EMPTY

        self.has_mine = False
        self.visible = False
        self.neighbours = None
        self.blocked = False

        self.current_image = self.parent().images.empty

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.pressed.connect(lambda item=self: item.parent().item_clicked(item))
        self.rightButtonPressed.connect(self.toggle_status)
        self.parent().items_block_released.connect(self.release_block)

    def paintEvent(self, QPaintEvent):
        super().paintEvent(QPaintEvent)
        painter = QPainter(self)

        painter.drawImage(
            self.rect().marginsAdded(QMargins() - 5),
            self.current_image
        )
        painter.end()

    def sizeHint(self):
        return QSize(50, 50)

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

            # print(f"Point's({self.y}, {self.x}) neighbours are:{neighbours_coords}")
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
        # EMPTY -> MINE -> QUESTIONABLE -> EMPTY ... etc.
        self.status = list(dropwhile(lambda x, c=self.status: x != c, chain.from_iterable(repeat(FieldState, 2))))[1]

        if self.status == FieldState.MINE:
            self.current_image = self.parent().images.flag_red
            self.parent().mines_found_count(1)
        elif self.status == FieldState.QUESTIONABLE:
            self.current_image = self.parent().images.question
            self.parent().mines_found_count(-1)
        else:
            self.current_image = self.parent().images.empty
        self.update()

    def show_any_state(self):
        self.visible = True

        parent = self.parent()
        neighbour_mines_count = sum(n.has_mine for n in self.neighbours)
        if neighbour_mines_count > 0 and not self.has_mine:
            self.current_image = parent.images.numbers[neighbour_mines_count]
        elif self.has_mine:
            self.current_image = parent.images.mine
        else:
            self.current_image = parent.images.checked
        self.update()


    def calculate(self):
        if self.blocked:  # or self.visible:
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
        self.status = FieldState.EMPTY
        self.current_image = self.parent().images.empty
        self.update()

    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.LeftButton:
            self.pressed.emit()
        elif e.button() == Qt.RightButton:
            self.rightButtonPressed.emit()
        else:
            print("Other button clicked")

    # TODO: FieldItem must stay squared!


class GameField(QWidget):
    mines_count_changed = pyqtSignal(int)
    game_started = pyqtSignal()
    game_ended = pyqtSignal()
    game_reset = pyqtSignal()
    items_block_released = pyqtSignal()

    def __init__(self, width=10, height=10, mines_count=10, *args, **kwargs):
        super(GameField, self).__init__(*args, **kwargs)

        self.width = width
        self.height = height
        self.mines_count = mines_count
        self.mines_found = 0
        self.images = self.parent().images
        self.game_run = False
        self.first_turn = True
        self.items_with_mines = []

        self.fieldItems2D = []
        layout = QGridLayout(self)
        layout.setSpacing(0)
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
        if self.mines_found == self.mines_count:
            mines_FieldItems_status =[i.status for i in self.items_with_mines]
            win_condition = set(mines_FieldItems_status) == set([FieldState.MINE])
            print(win_condition)
            if win_condition:
                print("You have won!")
                self.stop_game()

    def place_mines(self):
        mines_positions = set()
        total_field_positions = self.width * self.height
        while len(mines_positions) < self.mines_count:
            mines_positions.add(randint(0, total_field_positions - 1))

        self.items_with_mines = []
        for i, mines_position in enumerate(mines_positions):
            y, x = mines_position // self.width, mines_position % self.height
            print(f"#{i} - {mines_position}([{y},{x}])")
            self.items_with_mines.append(self.fieldItems2D[y][x])
            self.fieldItems2D[y][x].has_mine = True
            self.fieldItems2D[y][x].update()

    def item_clicked(self, item: FieldItem):
        # print(f"{item} clicked")
        if self.game_run:
            if item.has_mine and self.first_turn:
                print("Ha-ha, found mine on first turn!")
                item.has_mine = False
                found_new_mine_spot = False
                while not found_new_mine_spot:
                    current_item = choice(self.fieldItems)
                    if not current_item.has_mine:
                        print(f"Ok, that mine was moved to {current_item}")
                        current_item.has_mine = True
                        found_new_mine_spot = True
                item.calculate()

            elif item.has_mine:
                print("You loose!")
                item.current_image = self.images.mine
                self.game_run = False
                self.game_ended.emit()
            else:
                item.calculate()

            item.update()
            self.items_block_released.emit()

            self.first_turn = False

        else:
            self.start_game()
            self.item_clicked(item)

    def start_game(self):
        self.game_reset.emit()
        self.game_run = True
        self.first_turn = True
        self.game_started.emit()

    def stop_game(self):
        self.game_run = False
        list(map(FieldItem.show_any_state, self.fieldItems))
        timer = QTimer(self)
        timer.singleShot(3000, self.reset_game)

    def reset_game(self):
        list(map(FieldItem.reset, self.fieldItems))
        self.mines_found = 0
        self.game_run = False
        list(map(FieldItem.reset, self.fieldItems))
        self.place_mines()
        self.game_reset.emit()


class StatusBar(QWidget):
    def __init__(self, *args, **kwargs):
        super(StatusBar, self).__init__(*args, **kwargs)
        layout = QHBoxLayout()
        self.setLayout(layout)

        self.mine_img = QLabel(self)
        pixmap = QPixmap().fromImage(self.parent().images.mine, Qt.AutoColor)
        self.mine_img.setPixmap(pixmap)
        layout.addWidget(self.mine_img)

        self.mines_counter = QLCDNumber(self)
        self.mines_counter.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self.mines_counter)

        self.img = QLabel(self)
        pixmap = QPixmap().fromImage(self.parent().images.smile, Qt.AutoColor)
        # pixmap = QPixmap().fromImage(self.parent().images.dead, Qt.AutoColor)
        self.img.setPixmap(pixmap)
        # self.img.setFixedSize(pixmap.size())
        self.img.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.img)

        self.timer_counter = QLCDNumber(self)
        self.timer_counter.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self.timer_counter)
        self.timer = QTimer(self)

    def start_timer(self):
        try:
            self.timer.stop()
            self.timer.disconnect()
            del self.timer
        except Exception:
            pass
        self.timer = QTimer(self)
        self.timer_counter.display(0)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(lambda x=self.timer_counter: x.display(x.value() + 1))
        self.timer.start()

    def end_timer(self):
        self.timer.stop()
        self.timer.disconnect()
        del self.timer

    def update_counter(self, value):
        self.mines_counter.display(value)

    def reset(self):
        self.timer_counter.display(0)
        self.mines_counter.display(0)

    def sizeHint(self):
        return QSize(40, 60)


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.images = Images()

        self.mainWidget = QWidget(self)

        layout = QVBoxLayout(self)
        self.mainWidget.setLayout(layout)

        self.status_bar = StatusBar(self)
        layout.addWidget(self.status_bar)

        self.game_field = GameField(height=10, width=10, mines_count=10, parent=self)
        layout.addWidget(self.game_field)

        self.game_field.mines_count_changed.connect(self.status_bar.mines_counter.display)
        self.game_field.game_started.connect(self.status_bar.start_timer)
        self.game_field.game_ended.connect(self.status_bar.end_timer)
        self.game_field.game_reset.connect(self.status_bar.reset)


        self.setCentralWidget(self.mainWidget)
        self.show()


app = QApplication(sys.argv)
window = MainWindow()

app.exec_()
