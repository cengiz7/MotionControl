import time
import win32con
import win32gui
import wx
import wx.lib.newevent
from wx.lib.floatcanvas import FloatCanvas
from MotionControl.utils import logicals as lg
from math import fabs, pi, sin, cos
from cv2 import circle, line

# https://www.uihere.com/free-cliparts  ikonlar için kaynak 12-04
# global wx window frame variables
global cursor_wnd
global eightpen_wnd

DestroyApp, EVT_DESTROY_APP = wx.lib.newevent.NewEvent()
SwitchCase, EVT_SWTCH_CASE = wx.lib.newevent.NewEvent()
SwitchKeyboardPage, EVT_SWTCH_PAGE = wx.lib.newevent.NewEvent()
destroy_evnt = DestroyApp()
swtch_case_evnt = SwitchCase()
swtch_pg_evnt = SwitchKeyboardPage()

angle = 0  # +- [0-180] * pi / 180
scale_val = 2
firstx, firsty, radius, lastx, lasty = 0, 0, 0, 0, 0  # cordinates for cursor movement indications
window_size = [0, 0]
arrow_center = [0, 0]  # cordinates for arrow placement around the cursor circle
scaled_win_size = 0
circle_radius = 0
is_lowercase = False

turkce = ['A', 'E', 'İ', 'R', 'L', 'I', 'D', 'K', 'N', 'M',
          'Y', 'U', 'S', 'T', 'B', 'O', 'Ü', 'Ş', 'Z', 'G',
          'H', 'Ç', 'Ğ', 'C', 'V', 'P', 'Ö', 'F', 'J']  # 29 chars

turkce_lowercase = ['a', 'e', 'i', 'r', 'l', 'ı', 'd', 'k', 'n', 'm',
                    'y', 'u', 's', 't', 'b', 'o', 'ü', 'ş', 'z', 'g',
                    'h', 'ç', 'ğ', 'c', 'v', 'p', 'ö', 'f', 'j']  # 29 chars

# use with somestring.translate(xx_trans_tab)
to_lower_trans_tab = str.maketrans(''.join(turkce), ''.join(turkce_lowercase))
to_upper_trans_tab = str.maketrans(''.join(turkce_lowercase), ''.join(turkce))

alphabet_chars = turkce
# https://tr.wikipedia.org/wiki/T%C3%BCrk_alfabesindeki_harflerin_kullan%C4%B1m_s%C4%B1kl%C4%B1klar%C4%B1
special_chars = ['.', ',', '!', '?', '@', ':', '_',
                 '0', '1', '2', '3', '4', '5', '6',
                 '7', '8', '9', '\\', '(', '+', '-',
                 '*', '/', '=', '"', "'", '`', ';',
                 ')', '[', ']', '%', '<', '>', '^']

icon_names = [["next-page", "enter", "space", "backspace"], ["next-page", "capslock", "ctrl", "alt"]]


# currently not used anywhere
def calc_arrow_center(half_win_size, x, y):
    rate = 1.70  # multiply by 2.0 equals to full window size
    if half_win_size + fabs(x) + scale_val > half_win_size*rate:
        subt = half_win_size + fabs(x) + scale_val - half_win_size*rate
        devide_rate = subt/fabs(x)
        state = -1 if x < 0 else 1
        nx = x - (subt*state)   # new x value
        state = 1 if y < 0 else -1
        ny = y - ((fabs(y) - fabs(y)*devide_rate)*state)
        return [nx, ny]
    return [half_win_size + x, half_win_size + y]


def arrow_movement():
    global angle, scale_val, scaled_win_size, arrow_center
    distance, angle = lg.calcutale_distance_angle(firstx, firsty, lastx, lasty)
    if distance > radius:
        # print(angle * (180 / pi))
        scale_val = round((distance / radius) * circle_radius)
        # check if the scaled size smalled than 1/4 of wx frame
        if scale_val > scaled_win_size / 6:
            scale_val = scaled_win_size / 6

        arrow_center[0] = scaled_win_size / 2 + (cos(angle) * distance)  # (window center + x)
        arrow_center[1] = scaled_win_size / 2 - (sin(angle) * distance)  # (window center - y)
        # print(+(cos(angle) * distance), -(sin(angle) * distance))
        # arrow_center = calc_arrow_center(scaled_win_size/2, +(cos(angle) * distance), -(sin(angle) * distance))
    else:
        # set scale value 0 to hide arrow
        scale_val = 0


#  for drawing cursor indicator circles on the image
def draw_cursor_circles(image):
    circle(image, (int(firstx), int(firsty)), int(radius), (255, 0, 0), 2)
    circle(image, (int(lastx), int(lasty)), 5, (255, 255, 255), 3)
    line(image, (int(firstx), int(firsty)), (int(lastx), int(lasty)), (0, 255, 0), 2)
    return image


# get wx events as parameter and send it to the target window
def post_wx_event(target, event):
    wx.PostEvent(target, event)


# for shifting 8pen keyboard characters correctly
def shift_char_pos(mode, x, y, shift_val):
    # shift_val += 3*shift_val / 2**label maybe later
    if mode in [1, 4]:
        x -= shift_val
    elif mode in [0, 5]:
        x += shift_val
    elif mode in [2, 7]:
        y -= shift_val
    else:  # in [3, 6]
        y += shift_val
    return x, y


def calculate_char_pos(mode, x, y):
    if mode in [3, 4]:
        y = -y
    elif mode in [5, 6]:
        x, y = -x, -y
    elif mode in [7, 0]:
        x = -x
    return x, y


def arrange_keyboard_chars_n_lists(canvas, kradius, shift_val):
    global alphabet_chars, special_chars
    page1, page2 = [], []

    # insert '.'  and ','  chars at the first label of 8pen board(these are frequenly used chars)
    alphabet_chars.insert(5, special_chars.pop(0))
    alphabet_chars.insert(6, special_chars.pop(0))

    for i in range(0, 32 - len(alphabet_chars), 1):
        alphabet_chars.append(special_chars.pop(0))

    page_list = [page1, page2]
    for page, char_list in enumerate([alphabet_chars, special_chars]):
        px, py = kradius, kradius
        label = 1
        for i in range(1, len(char_list)+1):
            x, y = calculate_char_pos(i % 8, px + kradius / 2 * label, py + kradius / 2 * label)
            x, y = shift_char_pos(i % 8, x, y, shift_val)
            page_list[page].append(canvas.AddScaledTextBox(char_list[i - 1], (x, y), kradius * 0.4,
                                                           PadSize=kradius * 0.06, Position='cc',
                                                           LineStyle=None,
                                                           Alignment="center"  # BackgroundColor="Red",
                                                           ))
            if page:  # if page != 0
                page_list[page][-1].Hide()  # hide if its not page1 char

            if i % 8 == 0:
                label += 1
    return page_list


def arrange_keyboard_control_icons(icons_path, half_win_size, canvas):
    icons = [[], []]
    for i, page_icons in enumerate(icon_names):
        for k, icon in enumerate(page_icons):
            x = 0 if k in [0, 2] else (half_win_size if k == 1 else -half_win_size)
            y = 0 if k in [1, 3] else (half_win_size if k == 0 else -half_win_size)
            bmp = wx.Image(f'{icons_path}/{icon}.png', wx.BITMAP_TYPE_PNG).ConvertToBitmap()
            bitmap = canvas.AddScaledBitmap(bmp, (x, y), Height=half_win_size / 5, Position="cc")
            bitmap.Show() if i == 0 else bitmap.Hide()
            icons[i].append(bitmap)
    return icons


# TODO: change arrow picture function

class ShowFps:
    # fps_after_frames = calculate fps once at every each 3 frame
    fps_after_frames = 3
    total_frame_count = 0
    calculated_fps = 0
    check_time = None

    def __init__(self, desired_frame_count):
        self.fps_after_frames = desired_frame_count

    def start(self):
        self.check_time = time.time()

    def next(self):
        self.total_frame_count += 1
        if self.total_frame_count % self.fps_after_frames == 0:
            self.calculated_fps = (1 / (time.time() - self.check_time)) * self.fps_after_frames
            self.check_time = time.time()
        return self.calculated_fps


class CursorIndicatorWindow(wx.Frame):
    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, parent=None, id=wx.ID_ANY, title="Cursor Indicator Window",
                          size=(scaled_win_size, scaled_win_size),
                          style=(wx.FRAME_SHAPED
                                 | wx.FRAME_NO_TASKBAR
                                 | wx.STAY_ON_TOP
                                 | wx.BORDER_NONE
                                 | wx.TRANSPARENT_WINDOW)
                          )
        self.size = self.GetSize()
        # cordinates for center circle
        self.circle_centerx = self.size[0]/2
        self.circle_centery = self.size[1]/2
        self.arrow_img = wx.Image('./data/arrow_images/arrow1-500-190.png', wx.BITMAP_TYPE_PNG)
        # self.arrow_img = wx.Image('./data/arrow_images/arrow2-500-188.png', wx.BITMAP_TYPE_PNG)
        self.iw, self.ih = self.arrow_img.GetSize()
        hwnd = self.GetHandle()
        # Obtaining style settings from current extended window
        ext_style_settings = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        # Style options for making window click-through and like so
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ext_style_settings
                               | win32con.WS_EX_LAYERED
                               | win32con.WS_EX_TRANSPARENT
                               | win32con.WS_EX_COMPOSITED
                               | win32con.WS_EX_NOACTIVATE
                               | win32con.WS_EX_TOPMOST
                               )
        # Making click-through
        # http://msdn.microsoft.com/en-us/library/windows/desktop/ms633540%28v=vs.85%29.aspx
        win32gui.SetLayeredWindowAttributes(hwnd, 0x00ffffff, 255, win32con.LWA_COLORKEY | win32con.LWA_ALPHA)
        #self.SetTransparent(180)  # 0 ile görünmezyapabilirsin
        self.InitUI()

    def InitUI(self):
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(EVT_DESTROY_APP, self.ExitApp)
        self.Centre()
        self.Show(False)


    def OnPaint(self, e):
        # yardımcı kaynak
        # https://github.com/svn2github/wxPython/blob/master/3rdParty/FloatCanvas/Tests/GCTest.py
        dc = wx.PaintDC(self)
        dc.SetBackground(wx.Brush("White"))
        dc.Clear()
        gc = wx.GraphicsContext.Create(dc)
        path = gc.CreatePath()
        # gc.SetPen(wx.RED_PEN)
        # gc.SetPen(wx.Pen("Red", width=6, style=wx.PENSTYLE_USER_DASH))
        gc.SetPen(wx.Pen(wx.Colour(255, 255, 0, 200), width=12, style=wx.PENSTYLE_SHORT_DASH))
        path.AddCircle(self.circle_centerx, self.circle_centery, circle_radius)
        gc.StrokePath(path)
        # https://github.com/LuaDist/wxwidgets/blob/master/samples/rotate/rotate.cpp

        # display arrow only if scale val > 0
        if scale_val > 0:
            img = self.arrow_img.Scale(scale_val, round(self.ih * (scale_val/self.iw)), wx.IMAGE_QUALITY_HIGH)
            img = img.Rotate(angle, (img.GetWidth() / 2, img.GetHeight() / 2))
            # axis corrections begin #
            w = arrow_center[0] if -pi / 2 <= angle <= pi / 2 else arrow_center[0] - img.GetWidth()
            h = arrow_center[1] - img.GetHeight() if 0 <= angle else arrow_center[1]
            # axis corrections end #
            wx.ClientDC(self).DrawBitmap(img.ConvertToBitmap(), w, h, False)
            # print(self.iw, self.ih, scale_val, round(self.ih * (scale_val/self.iw)))

    def ExitApp(self, event=None):
        print("destroy event occurred")
        wx.Abort()


# kaynak https://github.com/wxWidgets/Phoenix/blob/master/demo/FloatCanvas.py
class KeyboardTrackingWindow(wx.Frame):
    is_custom_hide = False

    def __init__(self, *args, **kwargs):
        win_size = round(min(window_size) * 0.45)
        wx.Frame.__init__(self, parent=None, id=wx.ID_ANY, title="Motion Control",
                          size=(win_size, win_size), style=wx.CAPTION | wx.FRAME_NO_TASKBAR | wx.STAY_ON_TOP)
        self.win_size = win_size
        kradius = circle_radius
        diameter = kradius*2
        shift_val = kradius*0.80
        self.current_page = 0
        center_pt = (0.0, 0.0)
        rect_size = kradius*9
        line_min, line_max = kradius*0.8, kradius*3.5
        icons_path = "./data/icons"
        self.alpha_value = 255
        self.alpha_increment = 5
        self.change_alpha_timer = wx.Timer(self)
        self.change_alpha_timer.Start(50)
        self.is_mouse_over = False


        # Add the Canvas
        cs = FloatCanvas.FloatCanvas(self, -1, size=(win_size, win_size), Debug=0, BackgroundColor="WHITE")
        self.cs = cs

        cs.AddCircle(center_pt, Diameter=diameter, LineWidth=2, LineColor='Black')
        cs.AddLine([(line_min, line_min), (line_max, line_max)], LineWidth=kradius/10, LineColor="RED")
        cs.AddLine([(line_min, -line_min), (line_max, -line_max)], LineWidth=kradius/10, LineColor="GREEN")
        cs.AddLine([(-line_min, -line_min), (-line_max, -line_max)], LineWidth=kradius/10, LineColor="BLUE")
        cs.AddLine([(-line_min, line_min), (-line_max, line_max)], LineWidth=kradius/10, LineColor="YELLOW")
        cs.AddRectangle((-rect_size/2, -rect_size/2), (rect_size, rect_size),
                        LineWidth=3, FillColor=None, LineColor="Gray")

        self.center_text = cs.AddScaledTextBox('', center_pt, kradius * 0.6,
                                               PadSize=kradius * 0.06, Position='cc',
                                               LineStyle=None,
                                               Alignment="center",
                                               # BackgroundColor="Red",
                                               )
        self.indicator_circle = cs.AddCircle(center_pt, Diameter=kradius/2, LineWidth=1,
                                             LineColor='Red', FillColor="Yellow")

        # 2 pages of keyboard characters
        self.page_list = arrange_keyboard_chars_n_lists(cs, kradius, shift_val)
        self.control_icons = arrange_keyboard_control_icons(icons_path, rect_size*0.45, cs)
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(self.cs, 1, wx.GROW)
        del cs
        self.SetSizerAndFit(box)
        self.Bind(EVT_SWTCH_PAGE, self.switch_page)
        self.Bind(EVT_SWTCH_CASE, self.switch_lettercase)
        self.Bind(EVT_DESTROY_APP, self.ExitApp)
        self.Bind(wx.EVT_TIMER, self.check_cursor_pos)
        self.Bind(wx.EVT_TIMER, self.close_smoothly)
        self.Show(False)
        self.cs.ZoomToBB()


    def custom_show(self):
        if self.is_custom_hide:
            self.is_custom_hide = False
            time.sleep(0.055)  # avoid race condition
            self.alpha_value = 255
            self.SetTransparent(255)
            self.Show()
        if not self.IsShownOnScreen() and not self.is_custom_hide:
            self.alpha_value = 255
            self.SetTransparent(255)
            self.Show()

    def custom_hide(self):
        self.is_custom_hide = True

    # check if the mouse cursor inside the window or not ( to pause smooth close )
    def check_cursor_pos(self, event):
        mpos = wx.GetMousePosition()
        spos = self.GetScreenPosition()
        # print(mpos, spos)
        if spos.x <= mpos.x <= spos.x+self.win_size and spos.y <= mpos.y <= spos.y+self.win_size:
            self.is_mouse_over = True
        else:
            self.is_mouse_over = False
        event.Skip()

    def close_smoothly(self, event):
        if self.is_custom_hide:
            if not self.is_mouse_over:
                if self.alpha_value <= self.alpha_increment*2:
                    self.is_custom_hide = False
                    self.SetTransparent(0)
                    self.Hide()
                else:
                    self.alpha_value -= self.alpha_increment
                    self.SetTransparent(self.alpha_value)
        event.Skip()


    def switch_page(self, event):
        # hide current page chars and icons firstly
        [icon.Hide() for icon in self.control_icons[self.current_page]]
        [icon.Hide() for icon in self.page_list[self.current_page]]
        # show selected page chars and icons now
        [icon.Show() for icon in self.control_icons[0 if self.current_page else 1]]
        [icon.Show() for icon in self.page_list[0 if self.current_page else 1]]
        # change current page state
        self.current_page = 0 if self.current_page == 1 else 1
        self.cs.Draw(True)

    def switch_lettercase(self, event):
        global alphabet_chars, is_lowercase
        alphabet_chars = [ch.translate(to_upper_trans_tab if is_lowercase else to_lower_trans_tab) for ch in alphabet_chars]
        [txtbox.SetText(txtbox.String.translate(to_upper_trans_tab if is_lowercase else to_lower_trans_tab)) for txtbox in self.page_list[0]]
        is_lowercase = not is_lowercase

    def ExitApp(self, event=None):
        print("destroy event occurred")
        wx.Abort()


# Start wx app mainloop with a thread from main(darknet_video.py)
def wx_app_main():
    global cursor_wnd, eightpen_wnd, window_size, scaled_win_size, circle_radius
    app = wx.App()
    window_size = wx.GetDisplaySize()
    scaled_win_size = round(min(window_size) * 0.8)
    circle_radius = round(scaled_win_size / 15)
    cursor_wnd = CursorIndicatorWindow()
    eightpen_wnd = KeyboardTrackingWindow()
    app.MainLoop()
