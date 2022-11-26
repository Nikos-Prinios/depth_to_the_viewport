import bpy
import cv2
import mediapipe as mp
from mathutils import Vector

""" ESCAPE TO STOP THE SCRIPT """

""" initialization """

# Create empty target if it doesnt already exist
obj = []
for o in bpy.data.objects:
    obj.append(o.name)
if "viewport_target" in obj:
    print("Empty is already there")
else:
    bpy.ops.object.empty_add(type='PLAIN_AXES', align='WORLD', location=(0, 0, 0), scale=(.1, .1, .1))
    bpy.context.object.name = "viewport_target"

# Mediapipe
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh()

# OpenCV
cap = cv2.VideoCapture(-1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 160)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 120)
cap.set(cv2.CAP_PROP_FPS, 30)

# Vectors
old = Vector((0.0,0.0,0.0))
new = Vector((0.0,0.0,0.0))
target_obj = bpy.data.objects["viewport_target"]

# Offset factor (min 1)
factor = 10

""" Functions """
        
def view_update(new) :
    global old
    loc = (old - new) * factor
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            r3d = area.spaces.active.region_3d
            target  = area.spaces.active.region_3d.view_location
            cam = r3d.view_rotation
            target_obj.rotation_quaternion = cam
            target_obj.location = target
            i = target_obj.matrix_world.copy()
            i.invert()
            i_rot = loc @ i
            target_obj.location = target_obj.location + i_rot
            r3d.view_location = target_obj.location
            old = new

def face_loc(frame):
    h, w, _ = frame.shape
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = face_mesh.process(frame_rgb)
    new_loc = [0,0,0]
    try:
        for facial_landmarks in result.multi_face_landmarks:
            pt1 = facial_landmarks.landmark[6]
            new_loc[0] = -pt1.x -.5
            new_loc[1] = -pt1.y -.5
            new_loc[2] = -pt1.z -.5
            loc = Vector( (new_loc[0],new_loc[1],new_loc[2]) )
        return loc
    except :
        return Vector( (0.0,0.0,0.0) )

def face_track() :
    ret, frame = cap.read()
    new = face_loc(frame)
    view_update(new)

"""
"""

class ModalTimerOperator(bpy.types.Operator):
    bl_idname = "wm.modal_timer_operator"
    bl_label = "Modal Timer Operator"

    _timer = None

    def modal(self, context, event):
        if event.type in {'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            face_track()
        return {'PASS_THROUGH'}

    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        cap.release()
        cv2.destroyAllWindows()
        wm = context.window_manager
        wm.event_timer_remove(self._timer)

def menu_func(self, context):
    self.layout.operator(ModalTimerOperator.bl_idname, text=ModalTimerOperator.bl_label)

def register():
    bpy.utils.register_class(ModalTimerOperator)
    bpy.types.VIEW3D_MT_view.append(menu_func)

def unregister():
    bpy.utils.unregister_class(ModalTimerOperator)
    bpy.types.VIEW3D_MT_view.remove(menu_func)

if __name__ == "__main__":
    register()

    # test call
    bpy.ops.wm.modal_timer_operator()
