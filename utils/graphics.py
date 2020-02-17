import time
import win32con
import win32gui
import wx
import wx.lib.newevent
import wx.lib.colourdb
from wx.lib.floatcanvas import NavCanvas, FloatCanvas, Resources

from cv2 import circle, line


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
def draw_cursor_circles(image, firstx, firsty, radius, lastx, lasty):
    circle(image, (int(firstx), int(firsty)), int(radius), (255, 0, 0), 2)
    circle(image, (int(lastx), int(lasty)), 5, (255, 255, 255), 3)
    line(image, (int(firstx), int(firsty)), (int(lastx), int(lasty)), (0, 255, 0), 2)
    return image


global cursor_wnd  # wx window frame variables
global eightpen_wnd
ShowWindowEvent, EVT_SHOW_WINDOW = wx.lib.newevent.NewEvent()
HideWindowEvent, EVT_HIDE_WINDOW = wx.lib.newevent.NewEvent()
CursorParamsEvent, EVT_CURSOR_PRMS = wx.lib.newevent.NewEvent()
DestroyApp, EVT_DESTROY_APP = wx.lib.newevent.NewEvent()
show_evnt = ShowWindowEvent(attr1="Show window event occurred")
hide_evnt = HideWindowEvent(attr1="Hide window event occurred")
params_evnt = CursorParamsEvent(attr1=None)
destroy_evnt = DestroyApp()


# get wx events as parameter and send it to the target window
def post_wx_event(target, event):
    wx.PostEvent(target, event)


class CursorIndicatorWnd(wx.Frame):
    def __init__(self, parent, title):
        self.size = (600, 600)
        self.circle_centerx = self.size[0]/2
        self.circle_centery = self.size[1]/2
        super(CursorIndicatorWnd, self).__init__(parent, title=title, size=self.size,
                                                 style=(wx.CLIP_CHILDREN
                                                        | wx.STAY_ON_TOP
                                                        | wx.BORDER_NONE
                                                        ))
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
        # Setting frame translucent - byte value
        # self.SetTransparent(180)  # 0 yapabilirsin
        self.InitUI()

    def InitUI(self):
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(EVT_SHOW_WINDOW, self.ShowWnd)
        self.Bind(EVT_HIDE_WINDOW, self.HideWnd)
        self.Bind(EVT_DESTROY_APP, self.ClsApp)
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
        path.AddCircle(self.circle_centerx, self.circle_centery, 50.0)
        gc.StrokePath(path)


    def HideWnd(self, event):
        print(event.attr1)
        self.Hide()

    def ShowWnd(self, event):
        print(event.attr1)
        self.Show(True)

    def ClsApp(self, event):
        print("destroy event occurred")
        self.Destroy()
        wx.Abort()


class KeyboardTrackWindow:
    def __init__(self):
        pass


def wait_for_globals():
    while 'cursor_wnd' not in globals():
        time.sleep(0.1)
    return


# Start wx app mainloop with a thread
def wx_app_main():
    global cursor_wnd
    global eightpen_wnd
    app = wx.App()
    cursor_wnd = CursorIndicatorWnd(None, 'Drawing demo')
    app.MainLoop()
