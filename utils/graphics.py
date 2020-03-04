import time
import win32con
import win32gui
import wx
import wx.lib.newevent
from math import fabs, sqrt, pow, atan2, pi, sin, cos
from cv2 import circle, line

# wx window frame variables
global cursor_wnd
global eightpen_wnd

DestroyApp, EVT_DESTROY_APP = wx.lib.newevent.NewEvent()
destroy_evnt = DestroyApp()

angle = 0  # +- [0-180] * pi / 180
circle_radius = 50  # bunu sil sonradan
scale_val = 2
firstx, firsty, radius, lastx, lasty = 0, 0, 0, 0, 0  # cordinates for cursor movement indications
window_size = [0, 0]
arrow_center = [0, 0]  # cordinates for arrow placement around the cursor circle
scaled_win_size = 0  # pixels


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


#  for drawing cursor indicator circles on the image
def draw_cursor_circles(image):
    circle(image, (int(firstx), int(firsty)), int(radius), (255, 0, 0), 2)
    circle(image, (int(lastx), int(lasty)), 5, (255, 255, 255), 3)
    line(image, (int(firstx), int(firsty)), (int(lastx), int(lasty)), (0, 255, 0), 2)
    return image


# get wx events as parameter and send it to the target window
def post_wx_event(target, event):
    wx.PostEvent(target, event)


class CursorIndicatorWnd(wx.Frame):
    def __init__(self, *args, **kwargs):
        global circle_radius, scaled_win_size
        scaled_win_size = round(min(window_size) / 1.5)
        circle_radius = round(scaled_win_size / 15)
        wx.Frame.__init__(self, parent=None, id=wx.ID_ANY, title="Cursor Draw Demo",
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


class KeyboardTrackWindow:
    def __init__(self):
        pass


# burayı sil zaten gerek kalmayacak
def wait_for_globals():
    while 'cursor_wnd' not in globals():
        time.sleep(0.05)
    return


# Start wx app mainloop with a thread
def wx_app_main():
    global cursor_wnd
    global eightpen_wnd
    global window_size
    app = wx.App()
    window_size = wx.GetDisplaySize()
    cursor_wnd = CursorIndicatorWnd(None)
    app.MainLoop()


def calc_arrow_center(half_win_size, x, y):
    if half_win_size + fabs(x) + scale_val > half_win_size*0.7:
        subt = half_win_size + fabs(x) + scale_val - half_win_size*0.7
        devide_rate = subt/fabs(x)
        state = x - (x-1)


def arrow_movement():
    global angle, scale_val, scaled_win_size, arrow_center
    abs_x = lastx - firstx
    abs_y = firsty - lasty
    distance = sqrt(pow(fabs(abs_x), 2) + pow(fabs(abs_y), 2))  # hipotenus to detection center
    if distance > radius:
        angle = atan2(abs_y, abs_x)
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



