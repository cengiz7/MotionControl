import time
import win32con
import win32gui
import wx
import wx.lib.newevent
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
DestroyApp, EVT_DESTROY_APP = wx.lib.newevent.NewEvent()
destroy_evnt = DestroyApp()
angle = 0  # +- [0-180] * pi / 180
circle_radius = 50


# get wx events as parameter and send it to the target window
def post_wx_event(target, event):
    wx.PostEvent(target, event)


class CursorIndicatorWnd(wx.Frame):
    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, parent=None, id=wx.ID_ANY, title="Cursor Draw Demo", size=(700, 700),
                          style=(wx.FRAME_SHAPED
                                 | wx.FRAME_NO_TASKBAR
                                 | wx.STAY_ON_TOP
                                 #| wx.BORDER_NONE
                                 | wx.TRANSPARENT_WINDOW)
                          )
        self.size = self.GetSize()
        # cordinates for center circle
        self.circle_centerx = self.size[0]/2
        self.circle_centery = self.size[1]/2
        self.arrow_img = wx.Image('./data/arrow_images/arrow2-500-188.png', wx.BITMAP_TYPE_PNG)


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
        self.Show(True)



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
        # scale ettikten sonra center hesapla
        # scale edilmiş resmi rotate et
        img_centre = wx.Point(self.arrow_img.GetWidth() / 2, self.arrow_img.GetHeight() / 2)
        img = self.arrow_img.Rotate(angle, img_centre)
        wx.ClientDC(self).DrawBitmap(img.ConvertToBitmap(), 150, 150, False)


    def ExitApp(self, event=None):
        print("destroy event occurred")
        self.Destroy()
        wx.Abort()


class KeyboardTrackWindow:
    def __init__(self):
        pass


def wait_for_globals():
    while 'cursor_wnd' not in globals():
        time.sleep(0.05)
    return


# Start wx app mainloop with a thread
def wx_app_main():
    global cursor_wnd
    global eightpen_wnd
    app = wx.App()
    cursor_wnd = CursorIndicatorWnd(None)
    app.MainLoop()


# moving cursor indicator arrow withing a while loop in a thread for not to slow down other processes
def arrow_movement(arrow_movement_queue):
    while True:
        something = arrow_movement_queue.get()
        print(something)
