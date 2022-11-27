import bpy
import cv2
import numpy as np
import mediapipe as mp
from mathutils import Vector
import math

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
    bpy.context.object.rotation_mode = 'QUATERNION'

# Mediapipe
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh()

# OpenCV
cap = cv2.VideoCapture(-1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 160)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 120)
cap.set(cv2.CAP_PROP_FPS, 30)

# Vectors
old_location = Vector((0.0,0.0,0.0))
location = Vector((0.0,0.0,0.0))
old_distance = 0.0
target_obj = bpy.data.objects["viewport_target"]

# Offset factor (min 1)
location_factor = 10
zoom_factor = 30
zoom_buffer = []

""" Functions """
        
def view_update(location, distance) :
    global old_location, old_distance, zoom_buffer
    
    # calculate location and distance
    loc = (old_location - location) * location_factor
    zoom = (old_distance - distance) * zoom_factor
    zoom_buffer.append(zoom)
    if len(zoom_buffer) == 10:
        zoom_buffer.pop(0)
    zoom_mean = sum(zoom_buffer) / len(zoom_buffer) # smoothing the zoom a bit
    # update the viewport(s)
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            r3d = area.spaces.active.region_3d
            target  = area.spaces.active.region_3d.view_location
            target_obj.rotation_quaternion = r3d.view_rotation
            target_obj.location = target
            i = target_obj.matrix_world.copy()
            i.invert()
            i_rot = -loc @ i
            target_obj.location = target_obj.location + i_rot
            r3d.view_location = target_obj.location
            r3d.view_distance += zoom_mean
            
    # update variables for next round
    old_location = location
    old_distance = distance

def face_loc(frame):
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = face_mesh.process(frame_rgb)
    new_loc = [0,0,0]
    try:
        for facial_landmarks in result.multi_face_landmarks:
            
            # face position
            face = facial_landmarks.landmark[6]
            new_loc[0] = -face.x -.5
            new_loc[1] = -face.y -.5
            new_loc[2] = -face.z -.5
            loc = Vector( (new_loc[0],new_loc[1],new_loc[2]) )
            
            # eyes distance for zooming
            left = facial_landmarks.landmark[243]
            left_eye = [(left.x-.5),(left.y-.5)]
            right = facial_landmarks.landmark[463]
            right_eye = [(right.x-.5),(right.y-.5)]
            dist = math.dist([right_eye[0],right_eye[1]], [left_eye[0],left_eye[1]])
            
        return loc,dist
    except :
        return Vector( (0.0,0.0,0.0) ), 0.0

def face_track() :
    ret, frame = cap.read()
    location, distance = face_loc(frame)
    view_update(location, distance)

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

    # call
    bpy.ops.wm.modal_timer_operator()
