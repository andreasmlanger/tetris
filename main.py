"""
Yet another Tetris clone ;-)
"""

import os
import sys
import time
import random
import tkinter as tk
from ctypes import c_buffer, windll


AUDIO = True
AMBYLOPIA = False


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        # noinspection PyProtectedMember
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath('.'), relative_path)


class Tetris:
    def __init__(self, parent):
        root.resizable(False, False)
        parent.title('Tetris')
        self.parent = parent
        self.amblyopia = AMBYLOPIA
        self.amblyopia_color_1, self.amblyopia_color_2 = '#62FFFF', '#FF6562'
        self.audio = AUDIO
        self.board_width = 10
        self.board_height = 20
        self.square_width = 30
        self.width = self.square_width * self.board_width
        self.height = self.square_width * self.board_height
        self.start_tick_rate = 800
        self.tick_rate = self.start_tick_rate
        self.min_tick_rate = 50
        self.ticking = None
        self.level_increase = 10
        self.increase_factor = 0.8
        self.shapes = {'S': [['*', ''],
                             ['*', '*'],
                             ['', '*']],
                       'Z': [['', '*'],
                             ['*', '*'],
                             ['*', '']],
                       'R': [['*', '*'],
                             ['*', ''],
                             ['*', '']],
                       'L': [['*', ''],
                             ['*', ''],
                             ['*', '*']],
                       'O': [['*', '*'],
                             ['*', '*']],
                       'I': [['*'],
                             ['*'],
                             ['*'],
                             ['*']],
                       'T': [['*', '*', '*'],
                             ['', '*', '']]}
        for key in ('<Down>', '<Left>', '<Right>'):
            self.parent.bind(key, self.shift)
        self.parent.bind('<Up>', self.rotate)
        for key in ('<Prior>', '<Next>', '<space>'):
            self.parent.bind(key, self.snap)
        for key in ('<Escape>', 'p', 'P'):
            self.parent.bind(key, self.pause)
        self.parent.bind('n', self.draw_board)
        self.parent.bind('N', self.draw_board)
        self.parent.bind('g', self.toggle_guides)
        self.parent.bind('G', self.toggle_guides)
        self.parent.bind('a', self.toggle_mode)
        self.parent.bind('A', self.toggle_mode)
        self.parent.bind('m', self.toggle_audio)
        self.parent.bind('M', self.toggle_audio)
        self.canvas = None
        self.preview_canvas = None
        self.preview_piece = None
        self.active_piece = None
        self.piece_is_active = None
        self.spawning = None
        self.colors = None
        self.board = None
        self.field = None
        self.bag = None
        self.restart_time = None
        self.lost = None
        self.paused = False
        self.guides = None
        self.guide_lines = False
        self.guide_fill = ''
        self.high_score = self.load_high_score()
        self.high_score_var = tk.StringVar()
        self.high_score_label = tk.Label(root, textvariable=self.high_score_var, width=15, height=2,
                                         font=('Verdana', 14))
        self.high_score_label.grid(row=0, column=1)
        self.score = 0
        self.score_var = tk.StringVar()
        self.score_label = tk.Label(root, textvariable=self.score_var, width=15, height=2, font=('Verdana', 14))
        self.score_label.grid(row=1, column=1)
        self.level_var = tk.StringVar()
        self.level_label = tk.Label(root, textvariable=self.level_var, width=15, height=2, font=('Verdana', 14))
        self.level_label.grid(row=2, column=1)
        self.draw_board()
        root.geometry('+400+20')  # Move window to the middle

    @staticmethod
    def load_high_score():
        try:
            fw = open('high_score.txt', 'r')
            high_score = int(fw.read())
            fw.close()
            return high_score
        except (FileNotFoundError, ValueError):
            return 0

    def save_high_score(self):
        fw = open('high_score.txt', 'w')
        fw.write(str(self.high_score))
        fw.close()

    def toggle_mode(self, _=None):
        self.amblyopia = not self.amblyopia
        self.draw_board()

    def draw_board(self, _=None):
        if self.amblyopia:
            self.colors = {c: self.amblyopia_color_1 for c in 'SZRLOIT'}
            self.amblyopia_color_1, self.amblyopia_color_2 = self.amblyopia_color_2, self.amblyopia_color_1
        else:
            self.colors = {'S': '#3CB371',
                           'Z': '#C71585',
                           'R': '#1E90FF',
                           'L': '#F4A460',
                           'O': '#BA55D3',
                           'I': '#2F4F4F',
                           'T': '#FA8072'}
        if self.ticking:
            self.parent.after_cancel(self.ticking)
        if self.spawning:
            self.parent.after_cancel(self.spawning)
        self.high_score_var.set('HIGH SCORE\n' + str(self.high_score))
        self.score_var.set('LINES\n0')
        self.level_var.set('LEVEL\n1')
        self.board = [['' for _ in range(self.board_width)] for _ in range(self.board_height)]
        self.field = [[None for _ in range(self.board_width)] for _ in range(self.board_height)]
        if self.canvas:
            self.canvas.destroy()
        self.canvas = tk.Canvas(root, width=self.width + 4, height=self.height)
        self.canvas.grid(row=0, column=0, rowspan=4)
        self.canvas.create_line(0, self.height // 5, self.width + 4, self.height // 5, width=2, dash=(2, 4))
        self.canvas.create_line(self.width + 4, 0, self.width + 4, self.height, width=2)
        if self.preview_canvas:
            self.preview_canvas.destroy()
        self.preview_canvas = tk.Canvas(root, width=5 * self.square_width, height=5 * self.square_width)
        self.preview_canvas.grid(row=3, column=1)
        self.tick_rate = self.start_tick_rate
        self.score = 0
        self.piece_is_active = False
        self.paused = False
        self.bag = []
        self.preview()
        self.guides = [self.canvas.create_line(0, 0, 0, self.height),
                       self.canvas.create_line(self.width + 3, 0, self.width + 3, self.height)]
        if not self.guide_lines:
            self.canvas.itemconfig(self.guides[0], fill='')
            self.canvas.itemconfig(self.guides[1], fill='')
        self.spawning = self.parent.after(self.tick_rate, self.spawn)
        self.ticking = self.parent.after(self.tick_rate * 2, self.tick)
        self.lost = False
        if self.audio:
            self.restart_time = time.time() + self.play_sound('music', 'start')

    def toggle_guides(self, _=None):
        self.guide_lines = not self.guide_lines
        self.guide_fill = '' if self.guide_fill else 'black'
        self.canvas.itemconfig(self.guides[0], fill=self.guide_fill)
        self.canvas.itemconfig(self.guides[1], fill=self.guide_fill)
    
    def toggle_audio(self, _=None):
        self.audio = not self.audio
        if not self.audio:
            self.play_sound('music', 'stop')
        else:
            self.restart_time = time.time() + self.play_sound('music', 'start')

    def pause(self, _=None):
        if self.piece_is_active and not self.paused:
            if self.audio:
                self.play_sound('music', 'stop')
            self.paused = True
            self.piece_is_active = False
            self.parent.after_cancel(self.ticking)
        elif self.paused:
            if self.audio:
                self.restart_time = time.time() + self.play_sound('music', 'start')
            self.paused = False
            self.piece_is_active = True
            self.ticking = self.parent.after(self.tick_rate, self.tick)

    def check(self, shape, r, c, h, w):
        for row, squares in zip(range(r, r + h), shape):
            for column, square in zip(range(c, c + w), squares):
                if (row not in range(self.board_height) or column not in range(self.board_width) or
                   (square and self.board[row][column] == 'x')):
                    return
        return True
    
    def move(self, shape, r, c, h, w):
        square_indexes = iter(range(4))
        for row in self.board:  # remove shape from board
            row[:] = ['' if cell == '*' else cell for cell in row]
        for row, squares in zip(range(r, r + h), shape):  # put shape onto board and piece onto canvas
            for column, square in zip(range(c, c + w), squares):
                if square:
                    self.board[row][column] = square
                    square_idx = next(square_indexes)
                    coord = (column * self.square_width + 3, row * self.square_width,
                             (column + 1) * self.square_width + 3, (row + 1) * self.square_width)
                    self.active_piece.coords[square_idx] = coord
                    self.canvas.coords(self.active_piece.piece[square_idx], coord)
        self.active_piece.row = r
        self.active_piece.column = c
        self.active_piece.shape = shape
        self.move_guides(c, c + w)
        return True
        
    def check_and_move(self, shape, r, c, h, w):
        return self.check(shape, r, c, h, w) and self.move(shape, r, c, h, w)
        
    def rotate(self, _=None):
        if not self.piece_is_active:  # don't rotate if not yet spawned
            return
        if len(self.active_piece.shape) == len(self.active_piece.shape[0]):  # don't rotate if 2x2 block
            self.active_piece.rotation_index = self.active_piece.rotation_index
            return
        r = self.active_piece.row
        c = self.active_piece.column
        le = len(self.active_piece.shape)
        wi = len(self.active_piece.shape[0])
        x = c + wi // 2  # center column for old shape
        y = r + le // 2  # center row for old shape
        shape = self.rotate_array(self.active_piece.shape, 90)
        rotation_index = self.active_piece.rotation_index
        rotation_offsets = self.active_piece.rotation[rotation_index]
        rotation_index = (rotation_index + 1) % 4
        le = len(shape)  # length of new shape
        wi = len(shape[0])  # width of new shape
        rt = y - le // 2  # row of new shape
        ct = x - wi // 2  # column of new shape
        x_correction, y_correction = rotation_offsets
        rt += y_correction
        ct += x_correction
        if self.check_and_move(shape, rt, ct, le, wi):
            self.active_piece.rotation_index = rotation_index
            return
        for a, b in zip((0, 0, -1, 0, 0, -2, -1, -1), (-1, 1, 0, -2, 2, 0, -1, 1)):  # if rotation next to wall
            if self.check_and_move(shape, rt + a, ct + b, le, wi):
                self.active_piece.rotation_index = rotation_index
                return

    @staticmethod
    def rotate_array(array, angle):
        for i in range(angle // 90):
            array = list(zip(*array))[::-1]
        return array

    def tick(self):
        if self.piece_is_active:
            self.shift()
        self.ticking = self.parent.after(self.tick_rate, self.tick)
        if self.audio and time.time() > self.restart_time:
            self.restart_time = time.time() + self.play_sound('music', 'start')

    def shift(self, event=None):
        down = {'Down'}
        left = {'Left'}
        right = {'Right'}
        if not self.piece_is_active:
            return
        r = self.active_piece.row
        c = self.active_piece.column
        le = len(self.active_piece.shape)
        wi = len(self.active_piece.shape[0])
        direction = (event and event.keysym) or 'Down'
        if direction in left:
            rt = r
            ct = c - 1
        elif direction in right:
            rt = r
            ct = c + 1
        else:
            rt = r + 1  # row, temporary
            ct = c  # column, temporary
        success = self.check_and_move(self.active_piece.shape, rt, ct, le, wi)
        if direction in down and not success:
            if not self.active_piece.hover:
                self.settle()
            elif event is None:
                self.settle()

    def settle(self):
        self.piece_is_active = False
        for row in self.board:
            row[:] = ['x' if cell == '*' else cell for cell in row]
        for (x1, y1, x2, y2), identity in zip(self.active_piece.coords, self.active_piece.piece):
            self.field[y1 // self.square_width][x1 // self.square_width] = identity
        indices = [idx for idx, row in enumerate(self.board) if all(row)]
        if indices:  # clear rows, score logic, etc.
            self.score += len(indices)
            self.clear(indices)
            if self.score > self.high_score:
                self.high_score = self.score
                self.save_high_score()
            self.score_var.set('LINES\n{}'.format(self.score))
            self.level_var.set('LEVEL\n{}'.format(self.score // self.level_increase + 1))
            self.high_score_var.set('HIGH SCORE\n{}'.format(self.high_score))
            if self.tick_rate > self.min_tick_rate:
                self.tick_rate = int(self.start_tick_rate * self.increase_factor ** (self.score // self.level_increase))
        if any(any(row) for row in self.board[:4]):
            self.lose()
            return
        if self.audio and not indices:
            self.play_sound('settle', 'start')
        self.spawning = self.parent.after(self.tick_rate, self.spawn)
        if self.amblyopia:  # change color after settle
            s = min(c[0] for c in self.active_piece.coords) // 30
            r = self.active_piece.coords[0][1] // 30
            for y, ro in enumerate(self.active_piece.shape):
                for x, cell in enumerate(ro, start=s):
                    if cell:
                        identity = self.field[y + r][x]
                        self.canvas.itemconfig(identity, fill=self.amblyopia_color_1)

    def preview(self):
        self.preview_canvas.delete(tk.ALL)
        if not self.bag:
            self.bag = random.sample('SZRLOIT', 7)
        key = self.bag.pop()
        shape = self.rotate_array(self.shapes[key], random.choice((0, 90, 180, 270)))
        self.preview_piece = Shape(shape, key, [], 0, 0, [])
        right = self.square_width * (5 - len(shape[0])) // 2 + 2
        down = self.square_width * (5 - len(shape)) // 2
        for y, row in enumerate(shape):
            for x, cell in enumerate(row):
                if cell:
                    self.preview_piece.coords.append((self.square_width * x + right,
                                                      self.square_width * y + down,
                                                      self.square_width * (x + 1) + right,
                                                      self.square_width * (y + 1) + down))
                    self.preview_piece.piece.append(
                        self.preview_canvas.create_rectangle(self.preview_piece.coords[-1],
                                                             fill=self.colors[key],
                                                             width=0 if self.amblyopia else 3))
        self.preview_piece.rotation_index = 0
        self.preview_piece.i_nudge = (len(shape) < len(shape[0])) and 4 in (len(shape), len(shape[0]))
        self.preview_piece.row = self.preview_piece.i_nudge
        if 3 in (len(shape), len(shape[0])):
            self.preview_piece.rotation = [(0, 0), (1, 0), (-1, 1), (0, -1)]
        else:
            self.preview_piece.rotation = [(1, -1), (0, 1), (0, 0), (-1, 0)]
        if len(shape) < len(shape[0]):  # wide shape
            self.preview_piece.rotation_index += 1
    
    def move_guides(self, left, right):
        left *= self.square_width
        right *= self.square_width
        self.canvas.coords(self.guides[0], left + 2, 0, left + 2, self.height)
        self.canvas.coords(self.guides[1], right + 3, 0, right + 3, self.height)
    
    def spawn(self):
        self.piece_is_active = True
        self.active_piece = self.preview_piece
        self.preview()
        width = len(self.active_piece.shape[0])
        start = (10 - width) // 2
        self.active_piece.column = start
        self.active_piece.start = start
        self.active_piece.coords = []
        self.active_piece.piece = []
        for y, row in enumerate(self.active_piece.shape):
            self.board[y+self.active_piece.i_nudge][start:start+width] = self.active_piece.shape[y]
            for x, cell in enumerate(row, start=start):
                if cell:
                    self.active_piece.coords.append((self.square_width * x + 3,
                                                     self.square_width * (y + self.active_piece.i_nudge) + 3,
                                                     self.square_width * (x + 1) + 3,
                                                     self.square_width * (y + self.active_piece.i_nudge + 1) + 3))
                    self.active_piece.piece.append(
                        self.canvas.create_rectangle(self.active_piece.coords[-1],
                                                     fill=self.colors[self.active_piece.key],
                                                     width=0 if self.amblyopia else 3))
        self.move_guides(start, start+width)

    def lose(self):
        self.lost = True
        self.piece_is_active = False
        if self.audio:
            self.play_sound('lose', 'start')
            self.play_sound('music', 'stop')
        self.parent.after_cancel(self.ticking)
        self.parent.after_cancel(self.spawning)
        self.clear_iter(range(len(self.board)))
        self.canvas.create_text(self.width // 2, self.height // 2, text='GAME\nOVER',
                                font=('Verdana', self.height // 10), fill='black')
        self.preview_canvas = tk.Label(root, text="PRESS 'N'\nTO RESTART",
                                       width=15, height=6, font=('Verdana', 14))
        self.preview_canvas.grid(row=3, column=1)

    def snap(self, event=None):
        down = {'space'}
        left = {'Prior'}
        right = {'Next'}
        if not self.piece_is_active:
            return
        r = self.active_piece.row
        c = self.active_piece.column
        le = len(self.active_piece.shape)
        wi = len(self.active_piece.shape[0])
        direction = event.keysym
        while True:
            if self.check(self.active_piece.shape, r + (direction in down),
                          c + (direction in right)-(direction in left), le, wi):
                r += direction in down
                c += (direction in right) - (direction in left)
            else:
                break
        self.move(self.active_piece.shape, r, c, le, wi)
        if direction in down:
            self.settle()
    
    def clear(self, indices):
        if self.audio:
            self.play_sound('clear', 'start')
        for idx in indices:
            self.board.pop(idx)
            self.board.insert(0, ['' for _ in range(self.board_width)])
        self.clear_iter(indices)
    
    def clear_iter(self, indices, current_column=0):
        for row in indices:
            if row % 2:
                cc = current_column
            else:
                cc = self.board_width - current_column - 1
            field = self.field[row][cc]
            self.field[row][cc] = None
            self.canvas.delete(field)
        if current_column < self.board_width - 1:
            self.parent.after(50, self.clear_iter, indices, current_column + 1)
        else:
            for idx, row in enumerate(self.field):
                offset = sum(r > idx for r in indices)*self.square_width
                for square in row:
                    if square:
                        self.canvas.move(square, 0, offset)
            for row in indices:
                self.field.pop(row)
                self.field.insert(0, [None for _ in range(self.board_width)])

    @staticmethod
    def play_sound(sound, command):

        def win_command(*com):
            com = ' '.join(com).encode('utf-8')
            buf = c_buffer(255)
            windll.winmm.mciSendStringA(com, buf, 254, 0)
            return buf.value

        try:
            path = str(resource_path(r'data/' + sound + '.mp3'))
            win_command('open "' + path + '" alias', sound)
            win_command('set', sound, 'time format milliseconds')
            duration = win_command('status', sound, 'length').decode()
            if command == 'start':
                win_command('play', sound, 'from 0 to', duration)
                return int(duration) // 1000
            elif command == 'stop':
                win_command('stop', sound)
        except ValueError:
            return 0  # audio files missing


class Shape:
    def __init__(self, shape, key, piece, row, column, coords):
        self.shape = shape
        self.key = key
        self.piece = piece
        self._row = row
        self._rotation_index = 0
        self.column = column
        self.coords = coords
        self.hover_time = self.spin_time = time.perf_counter()

    @property
    def row(self):
        return self._row

    @row.setter
    def row(self, x):
        if x != self._row:
            self._row = x
            self.hover_time = time.perf_counter()

    @property
    def rotation_index(self):
        return self._rotation_index

    @rotation_index.setter
    def rotation_index(self, x):
        self._rotation_index = x
        self.spin_time = time.perf_counter()

    @property
    def hover(self):  # move piece before snapping down
        return time.perf_counter() - self.hover_time < 0.4

    @property
    def spin(self):  # don't rotate it indefinitely to keep it from falling
        return time.perf_counter() - self.spin_time < 0.4


root = tk.Tk()
tetris = Tetris(root)
root.iconbitmap(resource_path('data/icon.ico'))
root.mainloop()
