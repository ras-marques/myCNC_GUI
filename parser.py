import math
import numpy as np
from PySide import QtCore, QtGui
import serial
import sys
import time

__author__ = 'RubenMarques'


def round_to_step(number):
    if number % 25 > 12:
        number += 25
    number /= 25
    number *= 25
    return number


def interpret_line(line):
    filling_x = False
    filling_y = False
    filling_z = False
    filled_x = False
    filled_y = False
    filled_z = False

    x = ""
    y = ""
    z = ""

    for c in line[3:]:
        if c == "X":
            filling_x = True
            filled_x = True
        elif c == "Y":
            filling_y = True
            filled_y = True
        elif c == "Z":
            filling_z = True
            filled_z = True
        elif c == " ":
            filling_x = False
            filling_y = False
            filling_z = False
        elif filling_x:
            x += c
        elif filling_y:
            y += c
        elif filling_z:
            z += c

    if filled_x:
        x = int(round(float(x) * 1000))
    if filled_y:
        y = -int(round(float(y) * 1000))    # O referencial da maquina esta orientado com y a crescer de cima para baixo
                                            # e o referencial da placa esta orientado com y a crescer de baixo para
                                            # cima, o "-" serve para transformar um no outro
    if filled_z:
        z = int(round(float(z) * 1000))

    return x, y, z


def get_next_pos(line):
    x, y, z = interpret_line(line)

    if x != "":
        if x % 25 > 12:
            x += 25
        x /= 25
        x *= 25
    if y != "":
        if y % 25 > 12:
            y += 25
        y /= 25
        y *= 25
    if z != "":
        if z % 25 > 12:
            z += 25
        z /= 25
        z *= 25

    return x, y, z


class Machine:
    def __init__(self):
        self.x_absolute = 0
        self.y_absolute = 0
        self.z_absolute = 0
        self.next_x_absolute = 0
        self.next_y_absolute = 0
        self.next_z_absolute = 0
        self.next_x_absolute_backup = 0
        self.next_y_absolute_backup = 0
        self.next_z_absolute_backup = 0

        self.x_to_origin = 0
        self.y_to_origin = 0
        self.z_to_origin = 0
        self.next_x_to_origin = 0
        self.next_y_to_origin = 0
        self.next_z_to_origin = 0
        self.next_x_to_origin_backup = 0
        self.next_y_to_origin_backup = 0
        self.next_z_to_origin_backup = 0

        self.x_origin = 0
        self.y_origin = 0
        self.z_origin = 0
        self.x_size = 100
        self.y_size = 100
        self.z_size = 100

        self.z_origin_set = False
        self.origin_changed = False

    def adjust_machine_z_to_board(self):
        board_z = board.calculate_height(self.x_absolute, self.y_absolute)
        board_z_next = board.calculate_height(self.next_x_absolute, self.next_y_absolute)
        diff_board_z = board_z_next - board_z
        self.next_z_to_origin -= diff_board_z
        self.next_z_to_origin = round_to_step(self.next_z_to_origin)
        self.next_z_absolute -= diff_board_z
        self.next_z_absolute = round_to_step(self.next_z_absolute)

    def update_next_absolute_and_preview(self):
        self.next_x_absolute = self.next_x_to_origin + self.x_origin
        self.next_y_absolute = self.next_y_to_origin + self.y_origin
        self.next_z_absolute = self.next_z_to_origin + self.z_origin
        main_window.preview_frame.update()

    def update_position_and_preview(self):
        self.x_to_origin = self.next_x_to_origin
        self.y_to_origin = self.next_y_to_origin
        self.z_to_origin = self.next_z_to_origin
        self.x_absolute = self.next_x_absolute
        self.y_absolute = self.next_y_absolute
        self.z_absolute = self.next_z_absolute
        main_window.preview_frame.update()

    # Not used para ja
    def check_origin_changed(self):
        if self.origin_changed:
            self.origin_changed = False
            self.restore_next()
            self.print_pos()

    # Not used para ja
    def backup_next(self):
        self.next_x_absolute_backup = self.next_x_absolute
        self.next_y_absolute_backup = self.next_y_absolute
        self.next_z_absolute_backup = self.next_z_absolute
        self.next_x_to_origin_backup = self.next_x_to_origin
        self.next_y_to_origin_backup = self.next_y_to_origin
        self.next_z_to_origin_backup = self.next_z_to_origin

    # Not used para ja
    def restore_next(self):
        self.next_x_absolute = self.next_x_absolute_backup
        self.next_y_absolute = self.next_y_absolute_backup
        self.next_z_absolute = self.next_z_absolute_backup
        self.next_x_to_origin = self.next_x_to_origin_backup
        self.next_y_to_origin = self.next_y_to_origin_backup
        self.next_z_to_origin = self.next_z_to_origin_backup

    def print_pos(self):
        print("(" + str(machine.x_absolute) + "," + str(machine.y_absolute) + "," + str(
            machine.z_absolute) + ") pres pos absolute")
        print("(" + str(machine.next_x_absolute) + "," + str(machine.next_y_absolute) + "," + str(
            machine.next_z_absolute) + ") next pos absolute")
        print("(" + str(machine.x_to_origin) + "," + str(machine.y_to_origin) + "," + str(
            machine.z_to_origin) + ") pres pos to origin")
        print("(" + str(machine.next_x_to_origin) + "," + str(machine.next_y_to_origin) + "," + str(
            machine.next_z_to_origin) + ") next pos to origin")
        print("(" + str(machine.next_x_absolute - machine.x_absolute) + "," + str(machine.next_y_absolute - machine.y_absolute) + "," + str(
            machine.next_z_absolute - machine.z_absolute) + ") diff next")


class Board:
    def __init__(self):
        self.p = np.array([0, 0, -50000])
        self.q = np.array([0, 100, -50000])
        self.r = np.array([100, 0, -50000])
        self.p_set = False
        self.q_set = False
        self.r_set = False
        self.PQ = np.array([0, 0, 0])
        self.PR = np.array([0, 0, 0])
        self.n = np.array([0, 0, 0])
        self.a = 0
        self.b = 0
        self.c = 0
        self.d = 0
        self.x = 0
        self.y = 0
        self.z = 0
        self.calculate_plane()

    def define_p(self, x, y, z):
        self.p = np.array([x, y, z])
        print("p set to: " + str(self.p))
        self.p_set = True
        if self.p_set and self.q_set and self.r_set:
            self.calculate_plane()

    def define_q(self, x, y, z):
        self.q = np.array([x, y, z])
        self.q_set = True
        print("q set to: " + str(self.q))
        if self.p_set and self.q_set and self.r_set:
            self.calculate_plane()

    def define_r(self, x, y, z):
        self.r = np.array([x, y, z])
        self.r_set = True
        print("r set to: " + str(self.r))
        if self.p_set and self.q_set and self.r_set:
            self.calculate_plane()

    def calculate_plane(self):
        self.PQ = self.p - self.q
        self.PR = self.p - self.r
        self.n = np.cross(self.PQ, self.PR)
        self.a = int(self.n[0])
        self.b = int(self.n[1])
        self.c = int(self.n[2])
        self.x = int(self.p[0])
        self.y = int(self.p[1])
        self.z = int(self.p[2])
        self.d = -(self.a*self.x + self.b*self.y + self.c*self.z)

    def calculate_height(self, input_x, input_y):
        # print("input_x: " + str(input_x) + " | input_y: " + str(input_y))
        return (- self.d - self.a*input_x - self.b*input_y) / self.c


class PrintManager(QtCore.QThread):
    finished = QtCore.Signal(str)
    
    def __init__(self):
        QtCore.QThread.__init__(self)
        self.running = False
        self.gcode_array = []
        self.line_number = 1
        self.z_g82_up = 0
        self.z_g82_down = 0
        self.number_of_commands_queued = 0
        self.stop_gcode_file_job = False

    def load_gcode(self):
        machine.z_origin_set = False    # desta forma, quando muda a ferramenta, tem que tirar a origem primeiro ao
                                        # sondar a superficie

        self.gcode_array = []
        main_window.preview_frame.gcode_file.seek(0)
        for line in main_window.preview_frame.gcode_file:
            self.gcode_array.append(line)

    def run(self):
        self.line_number = 1
        for line in self.gcode_array:
            if self.stop_gcode_file_job:
                self.stop_gcode_file_job = False
                break
            print("")
            print(self.line_number)
            print(line),

            if line[0] == "(":  # esta linha e um comentario, ignorar
                pass
            elif line[0:3] == "G00" or line[0:3] == "G01":
                machine.next_x_to_origin, machine.next_y_to_origin, machine.next_z_to_origin = get_next_pos(line)

                if machine.next_x_to_origin == "":
                    machine.next_x_to_origin = machine.x_to_origin
                if machine.next_y_to_origin == "":
                    machine.next_y_to_origin = machine.y_to_origin
                if machine.next_z_to_origin == "":
                    machine.next_z_to_origin = machine.z_to_origin

                machine.adjust_machine_z_to_board()
                machine.update_next_absolute_and_preview()
                machine.print_pos()

                # inicialmente o programa comeca pausado by default, significando que precisa ser "despausado", e nessa
                # altura, a condicao seguinte deixa de se verificar (ver change_pause() ), porque
                # number_of_commands_queued passa a ser -1, em vez de 0, que e como este atributo do thread inicia
                while self.number_of_commands_queued == 0:
                    pass
                if self.number_of_commands_queued > 0:
                    self.number_of_commands_queued -= 1
                # machine.check_origin_changed()

                if self.stop_gcode_file_job:
                    self.stop_gcode_file_job = False
                    break

                if line[0:3] == "G00":
                    serial_thread.translatingspeed = main_window.translating_speed.value()
                elif line[0:3] == "G01":
                    serial_thread.translatingspeed = main_window.milling_speed.value()
                serial_thread.comm_mode = "next_xyz_to_origin"
                serial_thread.start()
                serial_thread.running = True

                while serial_thread.running:
                    pass
                machine.update_position_and_preview()

            elif line[0:3] == "G82":
                self.z_g82_up = machine.z_to_origin
                machine.next_x_to_origin, machine.next_y_to_origin, machine.next_z_to_origin = get_next_pos(line)

                if machine.next_x_to_origin == "":
                    machine.next_x_to_origin = machine.x_to_origin
                if machine.next_y_to_origin == "":
                    machine.next_y_to_origin = machine.y_to_origin
                if machine.next_z_to_origin != "":
                    self.z_g82_down = machine.next_z_to_origin
                    machine.next_z_to_origin = machine.z_to_origin # so no proximo comando e q "fura", neste apenas mexe os eixos x e y
                else:
                    machine.next_z_to_origin = machine.z_to_origin

                print("(" + str(machine.x_to_origin) + "," + str(machine.y_to_origin) + "," + str(machine.z_to_origin) + ") pres pos to origin")

                machine.adjust_machine_z_to_board()
                machine.update_next_absolute_and_preview()
                machine.print_pos()

                # ver a primeira ocorrencia desta rotina
                while self.number_of_commands_queued == 0:
                    pass
                if self.number_of_commands_queued > 0:
                    self.number_of_commands_queued -= 1
                # machine.check_origin_changed()

                if self.stop_gcode_file_job:
                    self.stop_gcode_file_job = False
                    break

                serial_thread.translatingspeed = main_window.translating_speed.value()
                serial_thread.comm_mode = "next_xyz_to_origin"
                serial_thread.start()
                serial_thread.running = True

                while serial_thread.running:
                    pass
                machine.update_position_and_preview()

                machine.next_x_to_origin = machine.x_to_origin
                machine.next_y_to_origin = machine.y_to_origin
                machine.next_z_to_origin = self.z_g82_down

                machine.adjust_machine_z_to_board()
                machine.update_next_absolute_and_preview()
                machine.print_pos()

                # ver a primeira ocorrencia desta rotina
                while self.number_of_commands_queued == 0:
                    pass
                if self.number_of_commands_queued > 0:
                    self.number_of_commands_queued -= 1
                # machine.check_origin_changed()

                if self.stop_gcode_file_job:
                    self.stop_gcode_file_job = False
                    break

                serial_thread.translatingspeed = main_window.milling_speed.value()
                serial_thread.comm_mode = "next_xyz_to_origin"
                serial_thread.start()
                serial_thread.running = True

                while serial_thread.running:
                    pass
                machine.update_position_and_preview()

                machine.next_x_to_origin = machine.x_to_origin
                machine.next_y_to_origin = machine.y_to_origin
                machine.next_z_to_origin = self.z_g82_up

                machine.adjust_machine_z_to_board()
                machine.update_next_absolute_and_preview()
                machine.print_pos()

                # ver a primeira ocorrencia desta rotina
                while self.number_of_commands_queued == 0:
                    pass
                if self.number_of_commands_queued > 0:
                    self.number_of_commands_queued -= 1
                # machine.check_origin_changed()

                if self.stop_gcode_file_job:
                    self.stop_gcode_file_job = False
                    break

                serial_thread.translatingspeed = main_window.translating_speed.value()
                serial_thread.comm_mode = "next_xyz_to_origin"
                serial_thread.start()
                serial_thread.running = True

                while serial_thread.running:
                    pass
                machine.update_position_and_preview()

            self.line_number += 1

            if not serial_thread.process_ok:
                main_window.sync_position()
                break

        self.running = False
        self.finished.emit("OK")


class CommsThread(QtCore.QThread):
    finished = QtCore.Signal(str)

    def __init__(self):
        QtCore.QThread.__init__(self)
        self.running = False
        self.process_ok = True
        self.ser = serial.Serial()
        self.end_of_line = 13
        self.buf = ''
        self.microsteps = 8
        self.translatingspeed = 1000
        self.next_x_readback = 0
        self.next_y_readback = 0
        self.next_z_readback = 0
        self.comm_mode = ""
        self.comm_ok = False

    def run(self):
        self.process_ok = True
        self.ser.baudrate = 115200
        self.ser.timeout = 0
        self.ser.port = 'COM13'

        self.ser.open()

        if self.comm_mode == "reset":
            self.comm_mode = ""
            self.write_microsteps()
            self.write_translatingspeed()
            self.reset()
            main_window.preview_frame.update()
            self.wait_for_done()
        elif self.comm_mode == "stop":
            self.comm_mode = ""
            self.stop()
        elif self.comm_mode == "sync_position":
            self.comm_mode = ""
            self.sync_position()
        elif self.comm_mode == "set_xy_origin":
            self.comm_mode = ""
            self.set_xy_origin()
        elif self.comm_mode == "set_z_origin":
            self.comm_mode = ""
            self.set_z_origin()
        elif self.comm_mode == "next_xyz_to_origin":
            self.comm_mode == ""
            self.write_microsteps()
            self.write_translatingspeed()
            self.write_next_pos_to_origin()
            self.wait_for_done()
        elif self.comm_mode == "next_xyz_absolute":
            self.comm_mode == ""
            self.write_microsteps()
            self.write_translatingspeed()
            self.write_next_pos_absolute()
            self.wait_for_done()
        elif self.comm_mode == "probe":
            self.comm_mode == ""
            self.write_microsteps()
            self.write_translatingspeed()
            self.write_probe()

        if not self.process_ok:
            self.reset()

        self.ser.close()
        
        machine.update_position_and_preview()

        self.running = False

    def write_microsteps(self):
        self.ser.write("microsteps")
        self.ser.write(chr(self.end_of_line))
        time.sleep(0.01)
        self.ser.write(str(self.microsteps))
        self.ser.write(chr(self.end_of_line))
        time.sleep(0.01)

    def write_translatingspeed(self):
        self.ser.write("translatingspeed")
        self.ser.write(chr(self.end_of_line))
        time.sleep(0.01)
        self.ser.write(str(self.translatingspeed))
        self.ser.write(chr(self.end_of_line))
        time.sleep(0.01)

    def write_next_pos_to_origin(self):
        self.ser.write("next_xyz_to_origin")
        self.ser.write(chr(self.end_of_line))
        time.sleep(0.01)
        self.ser.write("(")
        self.ser.write(str(machine.next_x_to_origin))
        self.ser.write(",")
        self.ser.write(str(machine.next_y_to_origin))
        self.ser.write(",")
        self.ser.write(str(machine.next_z_to_origin))
        self.ser.write(")")
        self.ser.write(chr(self.end_of_line))
        time.sleep(0.01)

        self.comm_ok = False
        while not self.comm_ok:
            self.wait_for_comm_ok_rel()

        self.ser.write("exe")
        self.ser.write(chr(self.end_of_line))
        time.sleep(0.01)

    def write_next_pos_absolute(self):
        self.ser.write("next_xyz_absolute")
        self.ser.write(chr(self.end_of_line))
        time.sleep(0.01)
        self.ser.write("(")
        self.ser.write(str(machine.next_x_absolute))
        self.ser.write(",")
        self.ser.write(str(machine.next_y_absolute))
        self.ser.write(",")
        self.ser.write(str(machine.next_z_absolute))
        self.ser.write(")")
        self.ser.write(chr(self.end_of_line))
        time.sleep(0.01)

        self.comm_ok = False
        while not self.comm_ok:
            self.wait_for_comm_ok_abs()

        self.ser.write("exe")
        self.ser.write(chr(self.end_of_line))
        time.sleep(0.01)

    def reset(self):
        self.ser.write("reset")
        self.ser.write(chr(self.end_of_line))
        time.sleep(0.01)

    def stop(self):
        self.ser.write("stop")
        self.ser.write(chr(self.end_of_line))
        time.sleep(0.01)

    def sync_position(self):
        self.ser.write("sync_position")
        self.ser.write(chr(self.end_of_line))
        time.sleep(0.01)
        while 1:
            try:
                inc = self.ser.read(1)
                self.buf += inc
                if inc == '!':
                    self.buf = self.buf.replace("!", "")
                    buffer1, buffer2, buffer3, buffer4, buffer5, buffer6 = self.buf.split(",")
                    machine.x_absolute = int(buffer1)
                    machine.y_absolute = int(buffer2)
                    machine.z_absolute = int(buffer3)
                    machine.next_x_absolute = machine.x_absolute
                    machine.next_y_absolute = machine.y_absolute
                    machine.next_z_absolute = machine.z_absolute
                    machine.x_origin = int(buffer4)
                    machine.y_origin = int(buffer5)
                    machine.z_origin = int(buffer6)

                    self.buf = ''
                    break
            except serial.SerialException as e:
                self.buf = ''
                print(str(e))
                break
            except:
                self.buf = ''
                print "Unexpected error during Sync Position:", sys.exc_info()[0]
                break

    def set_xy_origin(self):
        self.ser.write("set_xy_origin")
        self.ser.write(chr(self.end_of_line))
        time.sleep(0.01)

    def set_z_origin(self):
        self.ser.write("set_z_origin")
        self.ser.write(chr(self.end_of_line))
        time.sleep(0.01)

    def wait_for_comm_ok_rel(self):
        self.ser.write("readback_rel")
        self.ser.write(chr(self.end_of_line))
        time.sleep(0.01)
        while 1:
            try:
                inc = self.ser.read(1)
                self.buf += inc
                if inc == '!':
                    self.buf = self.buf.replace("!", "")
                    self.next_x_readback, self.next_y_readback, self.next_z_readback = self.buf.split(",")
                    if not (machine.next_x_to_origin == int(self.next_x_readback) and
                            machine.next_y_to_origin == int(self.next_y_readback) and
                            machine.next_z_to_origin == int(self.next_z_readback)):
                        self.comm_ok = False
                    else:
                        self.comm_ok = True
                    self.buf = ''
                    break
            except serial.SerialException as e:
                self.buf = ''
                print(str(e))
                self.comm_ok = False
                break
            except:
                self.buf = ''
                print "Unexpected error during Wait for comm ok rel:", sys.exc_info()[0]
                self.comm_ok = False
                break

    def wait_for_comm_ok_abs(self):
        self.ser.write("readback_abs")
        self.ser.write(chr(self.end_of_line))
        time.sleep(0.01)
        while 1:
            try:
                inc = self.ser.read(1)
                self.buf += inc
                if inc == '!':
                    self.buf = self.buf.replace("!", "")
                    self.next_x_readback, self.next_y_readback, self.next_z_readback = self.buf.split(",")

                    if not (machine.next_x_absolute == int(self.next_x_readback) and
                            machine.next_y_absolute == int(self.next_y_readback) and
                            machine.next_z_absolute == int(self.next_z_readback)):
                        self.comm_ok = False
                    else:
                        self.comm_ok = True
                    self.buf = ''
                    break
            except serial.SerialException as e:
                self.buf = ''
                print(str(e))
                self.comm_ok = False
                break
            except:
                self.buf = ''
                print "Unexpected error during Wait for comm ok abs:", sys.exc_info()[0]
                self.comm_ok = False
                break

    def wait_for_done(self):
        while 1:
            try:
                inc = self.ser.read(1)
                self.buf += inc
                if inc == '!':
                    if self.buf == "done!":
                        pass
                    elif self.buf == "interrupt!":
                        self.process_ok = False
                        print("interrupt")
                    else:
                        print("unexpected, received: "),
                        print(self.buf)
                    self.buf = ''
                    break
            except serial.SerialException as e:
                self.buf = ''
                print(str(e))
                self.comm_ok = False
                break
            except:
                self.buf = ''
                print "Unexpected error during Wait for done:", sys.exc_info()[0]
                self.comm_ok = False
                break

    def write_probe(self):
        self.ser.write("exeprobe")
        self.ser.write(chr(self.end_of_line))
        time.sleep(0.01)
        while 1:
            try:
                inc = self.ser.read(1)
                self.buf += inc
                if inc == '!':
                    self.buf = self.buf.replace("!", "")
                    # faz o update de next_z_absolute para z_absolute mais a frente no CommsThread
                    machine.next_z_absolute = int(self.buf)
                    # print(machine.next_z_absolute)
                    self.buf = ''
                    break
            except serial.SerialException as e:
                self.buf = ''
                print(str(e))
                self.comm_ok = False
                break
            except:
                self.buf = ''
                print "Unexpected error during Write probe:", sys.exc_info()[0]
                self.comm_ok = False
                break


class PreviewWindow(QtGui.QWidget):
    def __init__(self):
        super(PreviewWindow, self).__init__()
        self.window_scale = 4
        self.draw_scale = self.window_scale
        self.zoom_factor = 2
        self.z_preview_width = 70
        self.max_width = 327 * self.window_scale + self.z_preview_width
        self.max_height = 170 * self.window_scale
        self.set_size(self.max_width, self.max_height)
        self.z_window_scale = 1
        self.x_offset = 0
        self.y_offset = 0
        self.z_offset = 0
        self.x_drawing = 0
        self.y_drawing = 0
        self.z_drawing = 0
        self.x_drawing_prev = self.x_drawing
        self.y_drawing_prev = self.y_drawing
        self.z_drawing_prev = self.z_drawing
        self.x_mouse = 0
        self.y_mouse = 0
        self.gcode_file = 0
        self.gcode_array = []
        self.gcode_loaded_into_preview = False
        self.tool_size = 0.1

    def set_size(self, x, y):
        self.max_width = x
        self.max_height = y
        self.setFixedSize(x, y)
        # print(self.max_width)
        # print(self.max_height)
        self.update()

    def local_file(self, gcode):
        self.gcode_file = gcode
        self.gcode_loaded_into_preview = False

    def line_width_from_tool_size(self):
        return math.ceil(self.tool_size*self.draw_scale)

    def paintEvent(self, event):
        # max_width_default = 327000/1000*4+70 = 1378
        # max_height_default = 170000/1000*4 = 680
        self.max_width = machine.x_size/1000 * self.window_scale + self.z_preview_width
        self.max_height = machine.y_size/1000 * self.window_scale
        self.set_size(self.max_width,self.max_height)

        painter = QtGui.QPainter()
        painter.begin(self)

        painter.drawLine(self.z_preview_width, 0, self.max_width - 1, 0)                                      # horizontal cima
        painter.drawLine(self.z_preview_width, 0, self.z_preview_width, self.max_height - 1)                  # vertical esquerda
        painter.drawLine(self.z_preview_width, self.max_height - 1, self.max_width - 1, self.max_height - 1)  # horizontal baixo
        painter.drawLine(self.max_width - 1, 0, self.max_width - 1, self.max_height - 1)                      # vertical direita

        # area de trabalho util
        painter.setPen(QtGui.QPen(QtGui.QPen(QtCore.Qt.red, 1, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.BevelJoin)))
        painter.setBrush(QtGui.QColor(251, 180, 138))
        x = self.z_preview_width + self.x_offset
        y = self.y_offset
        width = (self.max_width - 1 - self.z_preview_width) * self.draw_scale / self.window_scale
        height = (self.max_height - 1) * self.draw_scale / self.window_scale
        if x < self.z_preview_width:
            width -= self.z_preview_width - x
            x = self.z_preview_width
        if y < 0:
            height -= - y
            y = 0
        painter.drawRect(x, y, width, height)
        # Igual mas com drawLine's
        # painter.drawLine(self.z_preview_width + self.x_offset, self.y_offset, self.z_preview_width + (self.max_width - 1 - self.z_preview_width) * self.draw_scale / self.window_scale + self.x_offset, self.y_offset)  # horizontal cima
        # painter.drawLine(self.z_preview_width + self.x_offset, self.y_offset, self.z_preview_width + self.x_offset, (self.max_height - 1) * self.draw_scale / self.window_scale + self.y_offset)  # vertical esquerda
        # painter.drawLine(self.z_preview_width + self.x_offset, (self.max_height - 1) * self.draw_scale / self.window_scale + self.y_offset, self.z_preview_width + (self.max_width - 1 - self.z_preview_width) * self.draw_scale / self.window_scale + self.x_offset, (self.max_height - 1) * self.draw_scale / self.window_scale + self.y_offset)  # horizontal baixo
        # painter.drawLine(self.z_preview_width + (self.max_width - 1 - self.z_preview_width) * self.draw_scale / self.window_scale + self.x_offset, self.y_offset, self.z_preview_width + (self.max_width - 1 - self.z_preview_width) * self.draw_scale / self.window_scale + self.x_offset, (self.max_height - 1) * self.draw_scale / self.window_scale + self.y_offset)  # vertical direita
        painter.setPen(QtGui.QPen(QtGui.QPen(QtCore.Qt.black, 1, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.BevelJoin)))
        # meio
        # painter.drawLine((self.z_preview_width+self.max_width - 1)/2, 0, (self.z_preview_width+self.max_width - 1)/2, self.max_height - 1)  # vertical meio
        # painter.drawLine(self.z_preview_width, (self.max_height - 1) / 2, self.max_width - 1, (self.max_height - 1) / 2)                    # horizontal meio

        painter.drawLine(self.z_preview_width + machine.x_origin / 1000. * self.draw_scale - 10 + self.x_offset,
                         machine.y_origin / 1000. * self.draw_scale - 1 + self.y_offset,
                         self.z_preview_width + machine.x_origin / 1000. * self.draw_scale + 10 + self.x_offset,
                         machine.y_origin / 1000. * self.draw_scale - 1 + self.y_offset)  # preview origem cruz
        painter.drawLine(self.z_preview_width + machine.x_origin / 1000. * self.draw_scale - 10 + self.x_offset,
                         machine.y_origin / 1000. * self.draw_scale + self.y_offset,
                         self.z_preview_width + machine.x_origin / 1000. * self.draw_scale + 10 + self.x_offset,
                         machine.y_origin / 1000. * self.draw_scale + self.y_offset)  # preview origem cruz
        painter.drawLine(self.z_preview_width + machine.x_origin / 1000. * self.draw_scale - 10 + self.x_offset,
                         machine.y_origin / 1000. * self.draw_scale + 1 + self.y_offset,
                         self.z_preview_width + machine.x_origin / 1000. * self.draw_scale + 10 + self.x_offset,
                         machine.y_origin / 1000. * self.draw_scale + 1 + self.y_offset)  # preview origem cruz
        painter.drawLine(self.z_preview_width + machine.x_origin / 1000. * self.draw_scale - 1 + self.x_offset,
                         machine.y_origin / 1000. * self.draw_scale - 10 + self.y_offset,
                         self.z_preview_width + machine.x_origin / 1000. * self.draw_scale - 1 + self.x_offset,
                         machine.y_origin / 1000. * self.draw_scale + 10 + self.y_offset)  # preview origem cruz
        painter.drawLine(self.z_preview_width + machine.x_origin / 1000. * self.draw_scale + self.x_offset,
                         machine.y_origin / 1000. * self.draw_scale - 10 + self.y_offset,
                         self.z_preview_width + machine.x_origin / 1000. * self.draw_scale + self.x_offset,
                         machine.y_origin / 1000. * self.draw_scale + 10 + self.y_offset)  # preview origem cruz
        painter.drawLine(self.z_preview_width + machine.x_origin / 1000. * self.draw_scale + 1 + self.x_offset,
                         machine.y_origin / 1000. * self.draw_scale - 10 + self.y_offset,
                         self.z_preview_width + machine.x_origin / 1000. * self.draw_scale + 1 + self.x_offset,
                         machine.y_origin / 1000. * self.draw_scale + 10 + self.y_offset)  # preview origem cruz

        painter.drawLine(self.z_preview_width, machine.y_absolute / 1000. * self.draw_scale + self.y_offset,
                         self.max_width - 1, machine.y_absolute / 1000. * self.draw_scale + self.y_offset)  # horizontal maquina
        painter.drawLine(self.z_preview_width + machine.x_absolute / 1000. * self.draw_scale + self.x_offset, 0,
                         self.z_preview_width + machine.x_absolute / 1000. * self.draw_scale + self.x_offset, self.max_height - 1)  # vertical maquina

        painter.drawLine(self.z_preview_width / 2 - 5, 0, self.z_preview_width / 2 - 5, self.max_height - 1)  # eixo z linha apenas

        if self.gcode_file != 0:
            if not self.gcode_loaded_into_preview:
                self.gcode_array = []
                self.gcode_file.seek(0)
                for line in self.gcode_file:
                    self.gcode_array.append(line)
                self.gcode_loaded_into_preview = True
            if self.gcode_loaded_into_preview:
                reading_tool_size = False
                for line in self.gcode_array:
                    # print("")
                    # print(line),
                    if line[0] == "(":  # esta linha e um comentario, ignorar
                        if line[0:13] == "(  Tool Size)":
                            reading_tool_size = True
                        elif reading_tool_size:
                            line = line.replace("(", "")
                            line = line.replace(" ", "")
                            line = line.replace(")", "")
                            self.tool_size = float(line)
                            reading_tool_size = False
                        continue
                    else:
                        self.x_drawing, self.y_drawing, self.z_drawing = get_next_pos(line)

                        if self.x_drawing == "":
                            self.x_drawing = self.x_drawing_prev
                        if self.y_drawing == "":
                            self.y_drawing = self.y_drawing_prev
                        if self.z_drawing == "":
                            self.z_drawing = self.z_drawing_prev

                        if line[0:3] == "G01":
                            painter.setPen(QtGui.QPen(QtGui.QPen(QtCore.Qt.black, self.line_width_from_tool_size(), QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.BevelJoin)))
                            painter.drawLine(self.z_preview_width + (machine.x_origin / 1000. + self.x_drawing_prev / 1000.) * self.draw_scale + self.x_offset,
                                             (machine.y_origin / 1000. + self.y_drawing_prev / 1000.) * self.draw_scale + self.y_offset,
                                             self.z_preview_width + (
                                             machine.x_origin / 1000. + self.x_drawing / 1000.) * self.draw_scale + self.x_offset,
                                             (machine.y_origin / 1000. + self.y_drawing / 1000.) * self.draw_scale + self.y_offset)

                        elif line[0:3] == "G82":
                            painter.setPen(QtGui.QPen(QtGui.QPen(QtCore.Qt.blue, 1, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.BevelJoin)))
                            painter.drawLine(-5 + self.z_preview_width + (machine.x_origin / 1000. + self.x_drawing / 1000.) * self.draw_scale + self.x_offset,
                                             -5 + (machine.y_origin / 1000. + self.y_drawing / 1000.) * self.draw_scale + self.y_offset,
                                             5 + self.z_preview_width + (machine.x_origin / 1000. + self.x_drawing / 1000.) * self.draw_scale + self.x_offset,
                                             5 + (machine.y_origin / 1000. + self.y_drawing / 1000.) * self.draw_scale + self.y_offset)
                            painter.drawLine(-5 + self.z_preview_width + (machine.x_origin / 1000. + self.x_drawing / 1000.) * self.draw_scale + self.x_offset,
                                             5 + (machine.y_origin / 1000. + self.y_drawing / 1000.) * self.draw_scale + self.y_offset,
                                             5 + self.z_preview_width + (machine.x_origin / 1000. + self.x_drawing / 1000.) * self.draw_scale + self.x_offset,
                                             -5 + (machine.y_origin / 1000. + self.y_drawing / 1000.) * self.draw_scale + self.y_offset)
                            painter.setPen(QtGui.QPen(QtGui.QPen(QtCore.Qt.black, 1, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.BevelJoin)))

                    self.x_drawing_prev = self.x_drawing
                    self.y_drawing_prev = self.y_drawing
                    self.z_drawing_prev = self.z_drawing

        self.z_window_scale = 1. * self.max_height / main_window.z_size.value()

        # indicador da posicao atual no eixo z
        painter.drawLine(self.z_preview_width / 2 - 5,
                         - (machine.z_absolute / 1000.) * self.z_window_scale,
                         self.z_preview_width / 2 - 5 - 10,
                         - (machine.z_absolute / 1000. * self.z_window_scale) + 10)
        painter.drawLine(self.z_preview_width / 2 - 5,
                         - (machine.z_absolute / 1000.) * self.z_window_scale,
                         self.z_preview_width / 2 - 5 - 10,
                         - (machine.z_absolute / 1000. * self.z_window_scale) - 10)

        # indicador da posicao seguinte no eixo z
        painter.drawLine(self.z_preview_width / 2 - 5,
                         - (machine.next_z_absolute / 1000.) * self.z_window_scale,
                         self.z_preview_width / 2 - 5 + 10,
                         - (machine.next_z_absolute / 1000. * self.z_window_scale) + 10)
        painter.drawLine(self.z_preview_width / 2 - 5,
                         - (machine.next_z_absolute / 1000.) * self.z_window_scale,
                         self.z_preview_width / 2 - 5 + 10,
                         - (machine.next_z_absolute / 1000. * self.z_window_scale) - 10)

        painter.drawLine(self.z_preview_width / 2 - 15, - machine.z_origin / 1000. * self.z_window_scale - 1,
                         self.z_preview_width / 2 + 5, - machine.z_origin / 1000. * self.z_window_scale - 1)  # z_origin
        painter.drawLine(self.z_preview_width / 2 - 15, - machine.z_origin / 1000. * self.z_window_scale,
                         self.z_preview_width / 2 + 5, - machine.z_origin / 1000. * self.z_window_scale)      # z_origin
        painter.drawLine(self.z_preview_width / 2 - 15, - machine.z_origin / 1000. * self.z_window_scale + 1,
                         self.z_preview_width / 2 + 5, - machine.z_origin / 1000. * self.z_window_scale + 1)  # z_origin

        painter.end()

    def mousePressEvent(self, event):
        if main_window.moveButton.isChecked():
            self.x_mouse = (event.x() - self.z_preview_width - self.x_offset)*1. / self.draw_scale
            if self.x_mouse < 0:
                self.x_mouse = 0
            elif self.x_mouse > (self.max_width - 1 - self.z_preview_width)*1. / self.window_scale:
                self.x_mouse = (self.max_width - 1 - self.z_preview_width)*1. / self.window_scale
            self.y_mouse = (event.y() - self.y_offset)*1. / self.draw_scale
            if self.y_mouse < 0:
                self.y_mouse = 0
            elif self.y_mouse > (self.max_height - 1)*1. / self.window_scale:
                self.y_mouse = (self.max_height - 1)*1. / self.window_scale
            # print("x_mouse: " + str(self.x_mouse) + "\ty_mouse: " + str(self.y_mouse))
            # print("x_offset: " + str(self.x_offset) + "\ty_offset: " + str(self.y_offset))
            machine.next_x_absolute = int(self.x_mouse * 1000)
            machine.next_y_absolute = int(self.y_mouse * 1000)
            machine.next_z_absolute = int(machine.z_absolute)
            serial_thread.translatingspeed = main_window.translating_speed.value()
            serial_thread.comm_mode = "next_xyz_absolute"
            serial_thread.start()
            serial_thread.running = True
        elif main_window.align_to_xyButton.isChecked():
            self.x_mouse = (event.x() - self.z_preview_width - self.x_offset)*1. / self.draw_scale
            if self.x_mouse < 0:
                self.x_mouse = 0
            elif self.x_mouse > (self.max_width - 1 - self.z_preview_width)*1. / self.window_scale:
                self.x_mouse = (self.max_width - 1 - self.z_preview_width)*1. / self.window_scale
            self.y_mouse = (event.y() - self.y_offset)*1. / self.draw_scale
            if self.y_mouse < 0:
                self.y_mouse = 0
            elif self.y_mouse > (self.max_height - 1)*1. / self.window_scale:
                self.y_mouse = (self.max_height - 1)*1. / self.window_scale
            # print("x_mouse: " + str(self.x_mouse) + "\ty_mouse: " + str(self.y_mouse))
            # print("x_offset: " + str(self.x_offset) + "\ty_offset: " + str(self.y_offset))
            machine.x_origin = int(machine.x_absolute - (self.x_mouse*1000 - machine.x_origin))  # ainda e preciso testar
            machine.y_origin = int(machine.y_absolute - (self.y_mouse*1000 - machine.y_origin))  # ainda e preciso testar
            serial_thread.comm_mode = "set_xy_origin"
            serial_thread.start()
            serial_thread.running = True
        elif main_window.zoom_inButton.isChecked():
            self.x_mouse = event.x() - self.z_preview_width - self.x_offset
            self.y_mouse = event.y() - self.y_offset
            self.x_offset = - (self.x_mouse - (self.max_width - 1 - self.z_preview_width) / (2 * self.zoom_factor))
            self.y_offset = - (self.y_mouse - (self.max_height - 1) / (2 * self.zoom_factor))
            # print("x_mouse: " + str(self.x_mouse) + "\ty_mouse: " + str(self.y_mouse))
            # print("x_offset: " + str(self.x_offset) + "\ty_offset: " + str(self.y_offset))
            self.draw_scale *= self.zoom_factor
            self.x_offset *= self.zoom_factor
            self.y_offset *= self.zoom_factor
        elif main_window.zoom_outButton.isChecked():
            self.x_mouse = event.x() - self.z_preview_width - self.x_offset
            self.y_mouse = event.y() - self.y_offset
            self.x_offset = - (self.x_mouse - (self.max_width - 1 - self.z_preview_width) / (2 / self.zoom_factor))
            self.y_offset = - (self.y_mouse - (self.max_height - 1) / (2 / self.zoom_factor))
            # print("x_mouse: " + str(self.x_mouse) + "\ty_mouse: " + str(self.y_mouse))
            # print("x_offset: " + str(self.x_offset) + "\ty_offset: " + str(self.y_offset))
            self.draw_scale /= self.zoom_factor*1.
            self.x_offset /= self.zoom_factor*1.
            self.y_offset /= self.zoom_factor*1.


class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.init_ui()
        self.update_size()

    def init_ui(self):
        self.setWindowTitle("My CNC control station")
        self.setGeometry(100, 100, 100, 100)

        self.appIcon = QtGui.QIcon('smiley.gif')
        self.setWindowIcon(self.appIcon)

        self.file = self.menuBar().addMenu("File")
        self.openAction = QtGui.QAction('Open', self, statusTip="Opens the file with the gcode for execution",
                                        triggered=self.show_dialog)
        self.file.addAction(self.openAction)
        self.quitAction = QtGui.QAction('Quit', self, statusTip="Quits the application", triggered=self.quit_app)
        self.file.addAction(self.quitAction)

        self.help = self.menuBar().addMenu("Help")
        self.aboutAction = QtGui.QAction('About', self, statusTip="Displays info about the program",
                                         triggered=self.about_help)
        self.help.addAction(self.aboutAction)

        self.myStatusBar = QtGui.QStatusBar()
        self.setStatusBar(self.myStatusBar)
        self.myStatusBar.showMessage('Ready', 2000)

        self.preview_frame = PreviewWindow()

        self.init_labels()

        self.init_user_input_widgets()

        self.init_layouts()

        self.central_widget = QtGui.QWidget()
        self.setCentralWidget(self.central_widget)
        self.central_widget.setLayout(self.HLayout1)

    def init_labels(self):
        self.step_xy_label = QtGui.QLabel('XY step (um)')
        self.step_z_label = QtGui.QLabel('Z step (um)')
        self.positioning_speed_label = QtGui.QLabel('Positioning speed (um/s)')
        self.translating_speed_label = QtGui.QLabel('Translating speed (um/s)')
        self.milling_speed_label = QtGui.QLabel('Milling speed (um/s)')
        self.dimm_label = QtGui.QLabel('Axis dimmensions (mm)')
        self.x_label = QtGui.QLabel('x = ')
        self.y_label = QtGui.QLabel('y = ')
        self.z_label = QtGui.QLabel('z = ')
        self.board_plane_label = QtGui.QLabel('Define board plane (optional)')

    def init_user_input_widgets(self):
        self.openButton = QtGui.QPushButton('Open')
        self.quitButton = QtGui.QPushButton('Quit')
        self.upButton = QtGui.QPushButton('+Z')
        self.downButton = QtGui.QPushButton('-Z')
        self.leftButton = QtGui.QPushButton('-X')
        self.rightButton = QtGui.QPushButton('+X')
        self.frontButton = QtGui.QPushButton('+Y')
        self.backButton = QtGui.QPushButton('-Y')
        self.set_xy_originButton = QtGui.QPushButton('Set XY Origin')
        self.set_z_originButton = QtGui.QPushButton('Set Z Origin')
        self.align_to_xyButton = QtGui.QPushButton('Align to XY')
        self.align_to_xyButton.setCheckable(True)
        self.go_to_originButton = QtGui.QPushButton('Go to Origin')
        self.go_to_toolchangeButton = QtGui.QPushButton('Go to ToolChange')
        self.sync_positionButton = QtGui.QPushButton('Sync Position')
        self.moveButton = QtGui.QPushButton('Move')
        self.moveButton.setCheckable(True)
        self.zoom_inButton = QtGui.QPushButton('Zoom In')
        self.zoom_inButton.setCheckable(True)
        self.zoom_outButton = QtGui.QPushButton('Zoom Out')
        self.zoom_outButton.setCheckable(True)
        self.reset_viewButton = QtGui.QPushButton('Reset View')
        self.positioning_speed = QtGui.QSpinBox()
        self.positioning_speed.setMinimum(1)
        self.positioning_speed.setSingleStep(1)
        self.positioning_speed.setMaximum(100000)
        self.positioning_speed.setValue(18000)
        self.positioning_speed.setAlignment(QtCore.Qt.AlignRight)
        self.translating_speed = QtGui.QSpinBox()
        self.translating_speed.setMinimum(1)
        self.translating_speed.setSingleStep(1)
        self.translating_speed.setMaximum(100000)
        self.translating_speed.setValue(5000)
        self.translating_speed.setAlignment(QtCore.Qt.AlignRight)
        self.milling_speed = QtGui.QSpinBox()
        self.milling_speed.setMinimum(1)
        self.milling_speed.setSingleStep(1)
        self.milling_speed.setMaximum(100000)
        self.milling_speed.setValue(1000)
        self.milling_speed.setAlignment(QtCore.Qt.AlignRight)
        self.x_size = QtGui.QSpinBox()
        self.x_size.setMinimum(1)
        self.x_size.setSingleStep(1)
        self.x_size.setMaximum(10000)
        self.x_size.setValue(327)
        self.x_size.setAlignment(QtCore.Qt.AlignRight)
        self.y_size = QtGui.QSpinBox()
        self.y_size.setMinimum(1)
        self.y_size.setSingleStep(1)
        self.y_size.setMaximum(10000)
        self.y_size.setValue(170)
        self.y_size.setAlignment(QtCore.Qt.AlignRight)
        self.step_xy_size = QtGui.QSpinBox()
        self.step_xy_size.setMinimum(0)
        self.step_xy_size.setSingleStep(25)
        self.step_xy_size.setMaximum(1000000)
        self.step_xy_size.setValue(1000)
        self.step_xy_size.setAlignment(QtCore.Qt.AlignRight)
        self.step_z_size = QtGui.QSpinBox()
        self.step_z_size.setMinimum(0)
        self.step_z_size.setSingleStep(25)
        self.step_z_size.setMaximum(1000000)
        self.step_z_size.setValue(1000)
        self.step_z_size.setAlignment(QtCore.Qt.AlignRight)
        self.z_size = QtGui.QSpinBox()
        self.z_size.setMinimum(1)
        self.z_size.setSingleStep(1)
        self.z_size.setMaximum(10000)
        self.z_size.setValue(78)
        self.z_size.setAlignment(QtCore.Qt.AlignRight)
        self.update_size_Button = QtGui.QPushButton('Update')
        self.define_p_Button = QtGui.QPushButton('Set point 1')
        self.define_q_Button = QtGui.QPushButton('Set point 2')
        self.define_r_Button = QtGui.QPushButton('Set point 3')
        self.pauseCheckbox = QtGui.QCheckBox('Pause', self)
        self.pauseCheckbox.toggle()
        self.next_commandButton = QtGui.QPushButton('Execute next command')
        self.resetButton = QtGui.QPushButton('Reset Axes')
        self.startButton = QtGui.QPushButton('Start')
        self.stopButton = QtGui.QPushButton('Stop')

        self.openButton.setFixedWidth(50)
        self.quitButton.setFixedWidth(50)
        self.upButton.setFixedWidth(50)
        self.downButton.setFixedWidth(50)
        self.leftButton.setFixedWidth(50)
        self.rightButton.setFixedWidth(50)
        self.frontButton.setFixedWidth(50)
        self.backButton.setFixedWidth(50)
        self.positioning_speed.setFixedWidth(60)
        self.translating_speed.setFixedWidth(60)
        self.milling_speed.setFixedWidth(60)
        self.x_size.setFixedWidth(60)
        self.y_size.setFixedWidth(60)
        self.z_size.setFixedWidth(60)

        self.openButton.clicked.connect(self.show_dialog)
        self.quitButton.clicked.connect(self.quit_app)
        self.leftButton.clicked.connect(self.move_left)
        self.rightButton.clicked.connect(self.move_right)
        self.backButton.clicked.connect(self.move_back)
        self.frontButton.clicked.connect(self.move_front)
        self.upButton.clicked.connect(self.move_up)
        self.downButton.clicked.connect(self.move_down)
        self.set_xy_originButton.clicked.connect(self.set_xy_origin)
        self.set_z_originButton.clicked.connect(self.set_z_origin)
        self.align_to_xyButton.clicked.connect(self.align_to_xy)
        self.go_to_originButton.clicked.connect(self.go_to_origin)
        self.go_to_toolchangeButton.clicked.connect(self.go_to_toolchange)
        self.sync_positionButton.clicked.connect(self.sync_position)
        self.moveButton.clicked.connect(self.select_move)
        self.zoom_inButton.clicked.connect(self.select_zoom_in)
        self.zoom_outButton.clicked.connect(self.select_zoom_out)
        self.reset_viewButton.clicked.connect(self.reset_view)
        self.update_size_Button.clicked.connect(self.update_size)
        self.define_p_Button.clicked.connect(self.define_p)
        self.define_q_Button.clicked.connect(self.define_q)
        self.define_r_Button.clicked.connect(self.define_r)
        self.pauseCheckbox.stateChanged.connect(self.change_pause)
        self.next_commandButton.clicked.connect(self.add_one_command_to_queue)
        self.resetButton.clicked.connect(self.reset_machine)
        self.startButton.clicked.connect(self.start_process)
        self.stopButton.clicked.connect(self.stop)

    def init_layouts(self):
        self.HLayout1 = QtGui.QHBoxLayout()
        self.VLayout1 = QtGui.QVBoxLayout()
        self.HLayout2 = QtGui.QHBoxLayout()
        self.VLayout2 = QtGui.QVBoxLayout()
        self.VLayout3 = QtGui.QVBoxLayout()
        self.HLayout3 = QtGui.QHBoxLayout()
        self.HLayout4 = QtGui.QHBoxLayout()
        self.VLayout4 = QtGui.QVBoxLayout()
        self.VLayout5 = QtGui.QVBoxLayout()
        self.HLayoutSetOrigin = QtGui.QHBoxLayout()
        self.HLayoutGoToAndSync = QtGui.QHBoxLayout()
        self.HLayoutClickOperation = QtGui.QHBoxLayout()
        self.HLayoutPosiSpeed = QtGui.QHBoxLayout()
        self.HLayoutTranSpeed = QtGui.QHBoxLayout()
        self.HLayoutMillSpeed = QtGui.QHBoxLayout()
        self.HLayoutXSize = QtGui.QHBoxLayout()
        self.HLayoutYSize = QtGui.QHBoxLayout()
        self.HLayoutZSize = QtGui.QHBoxLayout()
        self.HLayoutUpdateSize = QtGui.QHBoxLayout()
        self.HLayoutBoardPlaneLabel = QtGui.QHBoxLayout()
        self.HLayoutBoardPlaneButtons = QtGui.QHBoxLayout()
        self.HLayout5 = QtGui.QHBoxLayout()
        self.HLayout6 = QtGui.QHBoxLayout()

        self.HSeparator1 = QtGui.QFrame()
        self.HSeparator1.setFrameShape(QtGui.QFrame.HLine)
        self.HSeparator2 = QtGui.QFrame()
        self.HSeparator2.setFrameShape(QtGui.QFrame.HLine)
        self.HSeparator3 = QtGui.QFrame()
        self.HSeparator3.setFrameShape(QtGui.QFrame.HLine)
        self.VSeparator1 = QtGui.QFrame()
        self.VSeparator1.setFrameShape(QtGui.QFrame.VLine)
        self.HSeparator4 = QtGui.QFrame()
        self.HSeparator4.setFrameShape(QtGui.QFrame.HLine)

        self.VLayout1_widget = QtGui.QWidget()  # Para aceder ao comando que define a largura maxima do quadro
        self.VLayout1_widget.setLayout(self.VLayout1)  # tenho que meter o quadro dentro de um widget e definir sim a
        self.VLayout1_widget.setMaximumWidth(350)  # largura maxima do widget
        self.HLayout1.addWidget(self.VLayout1_widget)
        self.HLayout1.addWidget(self.VSeparator1)
        self.HLayout1.addWidget(self.preview_frame)
        self.HLayout1.addStretch()
        self.VLayout1.addLayout(self.HLayout2)
        self.VLayout1.addWidget(self.HSeparator1)
        self.VLayout1.addLayout(self.HLayout3)
        self.VLayout1.addLayout(self.HLayout4)
        self.VLayout1.addLayout(self.HLayoutPosiSpeed)
        self.VLayout1.addLayout(self.HLayoutTranSpeed)
        self.VLayout1.addLayout(self.HLayoutMillSpeed)
        self.VLayout1.addLayout(self.HLayoutClickOperation)
        self.VLayout1.addLayout(self.HLayoutSetOrigin)
        self.VLayout1.addLayout(self.HLayoutGoToAndSync)
        self.VLayout1.addWidget(self.HSeparator2)
        self.VLayout1.addLayout(self.HLayoutBoardPlaneLabel)
        self.VLayout1.addLayout(self.HLayoutBoardPlaneButtons)
        self.VLayout1.addWidget(self.HSeparator3)
        self.VLayout1.addWidget(self.dimm_label)
        self.VLayout1.addLayout(self.HLayoutXSize)
        self.VLayout1.addLayout(self.HLayoutYSize)
        self.VLayout1.addLayout(self.HLayoutZSize)
        self.VLayout1.addLayout(self.HLayoutUpdateSize)
        self.VLayout1.addWidget(self.HSeparator4)
        self.VLayout1.addStretch()
        self.VLayout1.addLayout(self.HLayout5)
        self.VLayout1.addLayout(self.HLayout6)
        self.HLayout2.addWidget(self.openButton)
        self.HLayout2.addWidget(self.quitButton)
        self.HLayout2.addStretch()
        self.HLayout3.addWidget(self.leftButton)
        self.HLayout3.addLayout(self.VLayout2)
        self.HLayout3.addWidget(self.rightButton)
        self.HLayout3.addSpacing(80)
        self.HLayout3.addLayout(self.VLayout3)
        self.HLayout3.addStretch()
        self.VLayout2.addWidget(self.backButton)
        self.VLayout2.addWidget(self.frontButton)
        self.HLayout4.addSpacing(40)
        self.HLayout4.addLayout(self.VLayout4)
        self.VLayout4.addWidget(self.step_xy_label)
        self.VLayout4.addWidget(self.step_xy_size)
        self.HLayout4.addSpacing(80)
        self.HLayout4.addLayout(self.VLayout5)
        self.VLayout5.addWidget(self.step_z_label)
        self.VLayout5.addWidget(self.step_z_size)
        self.VLayout3.addWidget(self.upButton)
        self.VLayout3.addWidget(self.downButton)
        self.HLayoutSetOrigin.addWidget(self.set_xy_originButton)
        self.HLayoutSetOrigin.addWidget(self.set_z_originButton)
        self.HLayoutSetOrigin.addWidget(self.align_to_xyButton)
        self.HLayoutGoToAndSync.addWidget(self.go_to_originButton)
        self.HLayoutGoToAndSync.addWidget(self.go_to_toolchangeButton)
        self.HLayoutGoToAndSync.addWidget(self.sync_positionButton)
        self.HLayoutClickOperation.addWidget(self.moveButton)
        self.HLayoutClickOperation.addWidget(self.zoom_inButton)
        self.HLayoutClickOperation.addWidget(self.zoom_outButton)
        self.HLayoutClickOperation.addWidget(self.reset_viewButton)
        self.HLayoutPosiSpeed.addWidget(self.positioning_speed_label)
        self.HLayoutPosiSpeed.addStretch()
        self.HLayoutPosiSpeed.addWidget(self.positioning_speed)
        self.HLayoutTranSpeed.addWidget(self.translating_speed_label)
        self.HLayoutTranSpeed.addStretch()
        self.HLayoutTranSpeed.addWidget(self.translating_speed)
        self.HLayoutMillSpeed.addWidget(self.milling_speed_label)
        self.HLayoutMillSpeed.addStretch()
        self.HLayoutMillSpeed.addWidget(self.milling_speed)
        self.HLayoutXSize.addWidget(self.x_label)
        self.HLayoutXSize.addWidget(self.x_size)
        self.HLayoutXSize.addStretch()
        self.HLayoutYSize.addWidget(self.y_label)
        self.HLayoutYSize.addWidget(self.y_size)
        self.HLayoutYSize.addStretch()
        self.HLayoutZSize.addWidget(self.z_label)
        self.HLayoutZSize.addWidget(self.z_size)
        self.HLayoutZSize.addStretch()
        self.HLayoutUpdateSize.addWidget(self.update_size_Button)
        self.HLayoutUpdateSize.addStretch()
        self.HLayoutBoardPlaneLabel.addWidget(self.board_plane_label)
        self.HLayoutBoardPlaneButtons.addWidget(self.define_p_Button)
        self.HLayoutBoardPlaneButtons.addWidget(self.define_q_Button)
        self.HLayoutBoardPlaneButtons.addWidget(self.define_r_Button)
        self.HLayout5.addWidget(self.pauseCheckbox)
        self.HLayout5.addWidget(self.next_commandButton)
        self.HLayout6.addWidget(self.resetButton)
        self.HLayout6.addWidget(self.startButton)
        self.HLayout6.addWidget(self.stopButton)
        self.HLayout6.addStretch()

    def move_left(self):
        print("x to left - present x ="),
        print(machine.x_absolute/1000.),
        print("next x ="),
        if machine.x_absolute >= self.step_xy_size.value():
            if printmanager_thread.running:
                machine.x_origin -= self.step_xy_size.value()
            machine.next_x_absolute = machine.x_absolute - self.step_xy_size.value()
            machine.next_y_absolute = machine.y_absolute
            machine.next_z_absolute = machine.z_absolute
            print(machine.x_absolute / 1000.)
            # E melhor nao fazer isto aqui
            # if board.p_set and board.q_set and board.r_set:
            #    machine.adjust_machine_z_to_board()
            serial_thread.translatingspeed = main_window.positioning_speed.value()
            serial_thread.comm_mode = "next_xyz_absolute"
            serial_thread.start()
            serial_thread.running = True
        else:
            print(machine.next_x_absolute / 1000.)

    def move_right(self):
        print("x to right - present x ="),
        print(machine.x_absolute/1000.),
        print("next x ="),
        if machine.x_absolute <= machine.x_size - self.step_xy_size.value():
            if printmanager_thread.running:
                machine.x_origin += self.step_xy_size.value()
            machine.next_x_absolute = machine.x_absolute + self.step_xy_size.value()
            machine.next_y_absolute = machine.y_absolute
            machine.next_z_absolute = machine.z_absolute
            print(machine.next_x_absolute / 1000.)
            # E melhor nao fazer isto aqui
            # if board.p_set and board.q_set and board.r_set:
            #    machine.adjust_machine_z_to_board()
            serial_thread.translatingspeed = main_window.positioning_speed.value()
            serial_thread.comm_mode = "next_xyz_absolute"
            serial_thread.start()
            serial_thread.running = True
        else:
            print(machine.next_x_absolute / 1000.)

    def move_back(self):
        print("y to back - present y ="),
        print(machine.y_absolute / 1000.),
        print("next y ="),
        if machine.next_y_absolute >= self.step_xy_size.value():
            if printmanager_thread.running:
                machine.y_origin -= self.step_xy_size.value()
            machine.next_x_absolute = machine.x_absolute
            machine.next_y_absolute = machine.y_absolute - self.step_xy_size.value()
            machine.next_z_absolute = machine.z_absolute
            print(machine.next_y_absolute / 1000.)
            # E melhor nao fazer isto aqui
            # if board.p_set and board.q_set and board.r_set:
            #    machine.adjust_machine_z_to_board()
            serial_thread.translatingspeed = main_window.positioning_speed.value()
            serial_thread.comm_mode = "next_xyz_absolute"
            serial_thread.start()
            serial_thread.running = True
        else:
            print(machine.next_y_absolute / 1000.)

    def move_front(self):
        print("y to front - present y ="),
        print(machine.y_absolute / 1000.),
        print("next y ="),
        if machine.next_y_absolute <= machine.y_size - self.step_xy_size.value():
            if printmanager_thread.running:
                machine.y_origin += self.step_xy_size.value()
            machine.next_x_absolute = machine.x_absolute
            machine.next_y_absolute = machine.y_absolute + self.step_xy_size.value()
            machine.next_z_absolute = machine.z_absolute
            print(machine.y_absolute / 1000.)
            # E melhor nao fazer isto aqui
            # if board.p_set and board.q_set and board.r_set:
            #    machine.adjust_machine_z_to_board()
            serial_thread.translatingspeed = main_window.positioning_speed.value()
            serial_thread.comm_mode = "next_xyz_absolute"
            serial_thread.start()
            serial_thread.running = True
        else:
            print(machine.next_y_absolute / 1000.)

    def move_up(self):
        print("z to up - present z ="),
        print(machine.z_absolute / 1000.),
        print("next z ="),
        if machine.next_z_absolute <= -self.step_z_size.value():
            if printmanager_thread.running:
                machine.z_origin += self.step_z_size.value()
            machine.next_x_absolute = machine.x_absolute
            machine.next_y_absolute = machine.y_absolute
            machine.next_z_absolute = machine.z_absolute + self.step_z_size.value()
            print(machine.next_z_absolute / 1000.)
            serial_thread.translatingspeed = main_window.positioning_speed.value()
            serial_thread.comm_mode = "next_xyz_absolute"
            serial_thread.start()
            serial_thread.running = True
        else:
            print(machine.next_z_absolute / 1000.)

    def move_down(self):
        print("z to down - present z ="),
        print(machine.z_absolute / 1000.),
        print("next z ="),
        if machine.next_z_absolute >= -machine.z_size+self.step_z_size.value():
            if printmanager_thread.running:
                machine.z_origin -= self.step_z_size.value()
            machine.next_x_absolute = machine.x_absolute
            machine.next_y_absolute = machine.y_absolute
            machine.next_z_absolute = machine.z_absolute - self.step_z_size.value()
            print(machine.next_z_absolute / 1000.)
            serial_thread.translatingspeed = main_window.positioning_speed.value()
            serial_thread.comm_mode = "next_xyz_absolute"
            serial_thread.start()
            serial_thread.running = True
        else:
            print(machine.next_z_absolute / 1000.)

    def set_xy_origin(self):
        machine.x_origin = machine.x_absolute
        machine.y_origin = machine.y_absolute
        self.preview_frame.update()
        serial_thread.comm_mode = "set_xy_origin"
        serial_thread.start()
        serial_thread.running = True

    def set_z_origin(self):
        machine.z_origin = machine.z_absolute
        print(machine.z_absolute)
        self.preview_frame.update()
        self.go_to_originButton.setEnabled(True)
        serial_thread.comm_mode = "set_z_origin"
        serial_thread.start()
        serial_thread.running = True
        machine.z_origin_set = True

    def align_to_xy(self):
        self.align_to_xyButton.setChecked(True)
        self.moveButton.setChecked(False)
        self.zoom_inButton.setChecked(False)
        self.zoom_outButton.setChecked(False)

    def go_to_origin(self):
        machine.next_x_absolute = machine.x_absolute
        machine.next_y_absolute = machine.y_absolute
        machine.next_z_absolute = -2000  # a 2mm do microswitch

        serial_thread.translatingspeed = main_window.translating_speed.value()
        serial_thread.comm_mode = "next_xyz_absolute"
        serial_thread.start()
        serial_thread.running = True

        print "Elevating tool"

        while serial_thread.running:
            pass

        machine.next_x_absolute = machine.x_origin
        machine.next_y_absolute = machine.y_origin
        machine.next_z_absolute = machine.z_absolute  # nao mexe

        serial_thread.translatingspeed = main_window.translating_speed.value()
        serial_thread.comm_mode = "next_xyz_absolute"
        serial_thread.start()
        serial_thread.running = True

        print "Positioning XY axis"

        while serial_thread.running:
            pass

        machine.next_x_absolute = machine.x_absolute
        machine.next_y_absolute = machine.y_absolute
        machine.next_z_absolute = machine.z_origin

        serial_thread.translatingspeed = main_window.translating_speed.value()
        serial_thread.comm_mode = "next_xyz_absolute"
        serial_thread.start()
        serial_thread.running = True

        print "Dropping tool to Z origin"

    def go_to_toolchange(self):
        machine.next_x_absolute = machine.x_absolute
        machine.next_y_absolute = machine.y_absolute
        machine.next_z_absolute = -2000  # a 2mm do microswitch

        self.go_to_originButton.setEnabled(False)

        serial_thread.translatingspeed = main_window.translating_speed.value()
        serial_thread.comm_mode = "next_xyz_absolute"
        serial_thread.start()
        serial_thread.running = True

    def sync_position(self):
        serial_thread.comm_mode = "sync_position"
        serial_thread.start()
        serial_thread.running = True

    def select_move(self):
        self.align_to_xyButton.setChecked(False)
        self.moveButton.setChecked(True)
        self.zoom_inButton.setChecked(False)
        self.zoom_outButton.setChecked(False)

    def select_zoom_in(self):
        self.align_to_xyButton.setChecked(False)
        self.moveButton.setChecked(False)
        self.zoom_inButton.setChecked(True)
        self.zoom_outButton.setChecked(False)

    def select_zoom_out(self):
        self.align_to_xyButton.setChecked(False)
        self.moveButton.setChecked(False)
        self.zoom_inButton.setChecked(False)
        self.zoom_outButton.setChecked(True)

    def reset_view(self):
        self.preview_frame.x_offset = 0
        self.preview_frame.y_offset = 0
        self.preview_frame.draw_scale = self.preview_frame.window_scale

    def update_size(self):
        machine.x_size = self.x_size.value() * 1000
        machine.y_size = self.y_size.value() * 1000
        machine.z_size = self.z_size.value() * 1000
        self.preview_frame.update()

    def change_pause(self, state):
        if state == QtCore.Qt.Checked:
            printmanager_thread.number_of_commands_queued = 0
        else:
            printmanager_thread.number_of_commands_queued = -1

    def add_one_command_to_queue(self):
        printmanager_thread.number_of_commands_queued += 1

    def make_a_square(self, size): # nao e usado atualmente, apenas para debug se for preciso
        machine.next_x_absolute = machine.x_absolute + size
        machine.next_y_absolute = machine.y_absolute
        machine.next_z_absolute = machine.z_absolute

        serial_thread.translatingspeed = main_window.milling_speed.value()
        serial_thread.comm_mode = "next_xyz_absolute"
        serial_thread.start()
        serial_thread.running = True

        while serial_thread.running:
            pass

        machine.next_x_absolute = machine.x_absolute
        machine.next_y_absolute = machine.y_absolute + size
        machine.next_z_absolute = machine.z_absolute

        serial_thread.translatingspeed = main_window.milling_speed.value()
        serial_thread.comm_mode = "next_xyz_absolute"
        serial_thread.start()
        serial_thread.running = True

        while serial_thread.running:
            pass

        machine.next_x_absolute = machine.x_absolute - size
        machine.next_y_absolute = machine.y_absolute
        machine.next_z_absolute = machine.z_absolute

        serial_thread.translatingspeed = main_window.milling_speed.value()
        serial_thread.comm_mode = "next_xyz_absolute"
        serial_thread.start()
        serial_thread.running = True

        while serial_thread.running:
            pass

        machine.next_x_absolute = machine.x_absolute
        machine.next_y_absolute = machine.y_absolute - size
        machine.next_z_absolute = machine.z_absolute

        serial_thread.translatingspeed = main_window.milling_speed.value()
        serial_thread.comm_mode = "next_xyz_absolute"
        serial_thread.start()
        serial_thread.running = True

        while serial_thread.running:
            pass

    def define_p(self):
        serial_thread.translatingspeed = main_window.positioning_speed.value()
        serial_thread.comm_mode = "probe"
        serial_thread.start()
        serial_thread.running = True
        while serial_thread.running:
            pass
        # print(machine.z_absolute)
        board.define_p(machine.x_absolute, machine.y_absolute, machine.z_absolute)
        if not machine.z_origin_set:
            self.set_z_origin()
            while serial_thread.running:
                pass
        machine.next_x_absolute = machine.x_absolute
        machine.next_y_absolute = machine.y_absolute
        machine.next_z_absolute = machine.z_absolute + 10000
        serial_thread.translatingspeed = main_window.positioning_speed.value()
        serial_thread.comm_mode = "next_xyz_absolute"
        serial_thread.start()
        serial_thread.running = True

    def define_q(self):
        serial_thread.translatingspeed = main_window.positioning_speed.value()
        serial_thread.comm_mode = "probe"
        serial_thread.start()
        serial_thread.running = True
        while serial_thread.running:
            pass
        # print(machine.z_absolute)
        board.define_q(machine.x_absolute, machine.y_absolute, machine.z_absolute)
        if not machine.z_origin_set:
            self.set_z_origin()
            while serial_thread.running:
                pass
        machine.next_x_absolute = machine.x_absolute
        machine.next_y_absolute = machine.y_absolute
        machine.next_z_absolute = machine.z_absolute + 10000
        serial_thread.translatingspeed = main_window.positioning_speed.value()
        serial_thread.comm_mode = "next_xyz_absolute"
        serial_thread.start()
        serial_thread.running = True

    def define_r(self):
        serial_thread.translatingspeed = main_window.positioning_speed.value()
        serial_thread.comm_mode = "probe"
        serial_thread.start()
        serial_thread.running = True
        while serial_thread.running:
            pass
        # print(machine.z_absolute)
        board.define_r(machine.x_absolute, machine.y_absolute, machine.z_absolute)
        if not machine.z_origin_set:
            self.set_z_origin()
            while serial_thread.running:
                pass
        machine.next_x_absolute = machine.x_absolute
        machine.next_y_absolute = machine.y_absolute
        machine.next_z_absolute = machine.z_absolute + 10000
        serial_thread.translatingspeed = main_window.positioning_speed.value()
        serial_thread.comm_mode = "next_xyz_absolute"
        serial_thread.start()
        serial_thread.running = True

    def quit_app(self):
        user_info = QtGui.QMessageBox.question(self, 'Confirmation',
                                               "This will quit the application. Do you want to Continue?",
                                               QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        if user_info == QtGui.QMessageBox.Yes:
            myApp.quit()
        if user_info == QtGui.QMessageBox.No:
            pass

    def about_help(self):
        QtGui.QMessageBox.about(self, "About My CNC control station",
                                "Programmed by Ruben Marques\nv0.01 - 04/04/2015\nPortugal")

    def show_dialog(self):
        file_name, _ = QtGui.QFileDialog.getOpenFileName(self, "Open GCode Files", "c:/", "GCode files(*.tap)")
        self.contents = open(file_name, 'r')
        self.preview_frame.local_file(self.contents)
        self.preview_frame.update()

    def show_finished(self):
        pass

    def reset_machine(self):
        machine.next_x_absolute = 0
        machine.next_y_absolute = 0
        machine.next_z_absolute = 0
        machine.x_origin = 0
        machine.y_origin = 0
        machine.z_origin = 0
        serial_thread.translatingspeed = 15000  # always the same, hard coded, yes, whats the problem...
        serial_thread.comm_mode = "reset"
        serial_thread.start()
        serial_thread.running = True

    def stop(self):
        serial_thread.comm_mode = "stop"
        serial_thread.start()
        printmanager_thread.stop_gcode_file_job = True
        printmanager_thread.running = True
        self.sync_position()

    def start_process(self):
        printmanager_thread.load_gcode()
        printmanager_thread.start()
        printmanager_thread.running = True


if __name__ == '__main__':
    try:
        machine = Machine()
        board = Board()
        myApp = QtGui.QApplication(sys.argv)
        main_window = MainWindow()
        main_window.show()
        serial_thread = CommsThread()
        serial_thread.finished.connect(main_window.show_finished, QtCore.Qt.QueuedConnection)
        printmanager_thread = PrintManager()
        printmanager_thread.finished.connect(main_window.show_finished, QtCore.Qt.QueuedConnection)
        myApp.exec_()
        sys.exit()
    except SystemExit:
        print("Closing CNC Interface...")
