'''
 ---- RUN ME FIRST !!!!!!!!!!!!!!!!!   ---------^ (click that little |> shaped arrow to the right of the 'IK_FK_Switcher.py' text)

then with the bones selected exactly as shown, select the menu item 'Pose->IK_FK_Switcher->Create IK Assembly' and you're done!

continue reading for more documentation below.



-------------------------------------------------------------------------------------------------------
Copyright 2024 by Ron Stanions (Malendryn Tiger) -- malendryn@gmail.com

This plugin is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

A copy of the GNU General Public License can be found here: <https://www.gnu.org/licenses/>.

This plugin is distributed WITHOUT ANY WARRANTY; without even the implied warranty of merchantability or
fitness for a particular purpose. See the GNU General Public License for more details.
-------------------------------------------------------------------------------------------------------

A super-simple IK<-->FK bone switcher that doesn't require the deform chain be copied to IK and FK chains.

Note:  This switcher is purely IK or FK and does not use any influence settings at all

Added bonuses: select all the right bones and with one menu selection, it'll create the entire IK constraint structure!
               with another menu selection it'll remove the entire IK structure and leave the pose exactly as placed!

to use: creating an IK bone chain
    create a series of connected bones like you normally would. (add a single bone, enter edit mode, extrude,extrude...)
    extrude a single bone somewhere along that bone chain to be your IK manipulator.
    name this bone anything you want, but it MUST have '_IK' in it somewhere!

    switch to pose mode and select all the bones you want affected by the _IK bone, plus ONLY the bones immediately after the _IK
    bone that you want the _IK manipulator to rotate
    finally select the bone with _IK in the name last

    select 'Pose->IK-FK Switcher->Create IK Assembly' and BAM!  You're ready to roll!

You can manually create your own IK setup too of course, just make sure you have that _IK bone!

to switch between IK and FK modes, 
    1) In Pose Mode: click on the _IK bone and choose the appropriate entry from the 'Pose->IK-FK Switcher menu'
and that's IT!  now you can pose your bones in either mode! 

Advantages:
    No copies of the bone chain, it all works on the original bones!
    When in FK mode any bones past the IK controlling bone are also FK as well (atypical of most setups I've seen)

Disadvantages(?):   
    Works exclusively on all-or-nothing switching, and does not apply any influences (which I think covers most use-cases!)
'''

import bpy
import pdb


def breaker19():
    D = getIKFKControlledBonesFromSelectedIKBone() # get and breakdown into convenience variables for use in the debugger
    IB = D["ikBone"]
    IC = D["ikChOf"]
    CB = D["ctlBone"]
    CC = D["ctlCons"]
    pdb.set_trace()


def applyVisualTransform(posebone, constraint):
        curbone = posebone
        for count in range(constraint.chain_count, 0, -1):  # mark this and all parent bones up to chain_count as selected
            # print("countdown=",count)
            # print("bone=", curbone.name)
            curbone.bone.select = True
            curbone = curbone.parent
        bpy.ops.pose.visual_transform_apply()       #apply the transformation

        curbone = posebone                          # now unselect those bones leaving just the IK bone selected again
        for count in range(constraint.chain_count, 0, -1):  # mark this and all parent bones up to chain_count as selected
            # print("countdown=",count)
            # print("bone=", curbone.name)
            curbone.bone.select = False
            curbone = curbone.parent

#RSTODO now that we know more about matrix relocation of the parented bones, lets see if we can remove the 'Child Of' constraint off the _IK bone
#   and do actual reparenting
def IK_to_FK():
    data = getIKFKControlledBonesFromSelectedIKBone()
    if data:
        posebone,constraint = (data["ctlBone"], data["ctlCons"])
        applyVisualTransform(posebone, constraint)
        constraint.mute = True                      #THEN turn off influence to make this fully FK now...
        if data["ikChOf"]:
            data["ikChOf"].mute = False             # ...awaken the child modifier and set the inverse!
            data["ikChOf"].inverse_matrix = data["ikChOf"].target.matrix_world.inverted()
            data["ikChOf"].set_inverse_pending = True
        data["ikBone"].color.palette = 'THEME02'


def FK_to_IK():
    data = getIKFKControlledBonesFromSelectedIKBone()
    if data:
        ikBone,ctlBone,ctlCons = (data["ikBone"], data["ctlBone"], data["ctlCons"])
        applyVisualTransform(ctlBone, ctlCons)
# RSTODO fixup the position of the pole bone here too (heres the new code but its still slightly glitchy, can we improve it?)

        endBone = ctlBone
        for idx in range(ctlCons.chain_count - 1, 0, -1):  # go up the IK chain to the first affected bone
            endBone = endBone.parent
        
        poleBone = ctlCons.pole_target.pose.bones.get(ctlCons.pole_subtarget)

#        poleBone.location = ctlBone.location
        # poleMatrix = bpy.context.object.matrix_world @ poleBone.matrix
        # poleBone.location = (0, 0, 0)
        # poleBone.matrix = bpy.context.object.matrix_world.inverted() @ poleMatrix

#        poleBone.location.y += 1

        [poleLoc, rollAngle] = getPoleLocAndAngle(endBone, ctlBone, poleBone.matrix.translation)
#RSTODO we should be able to remove thie 'poleLoc' return val entirely from getPoleLocAndAngle

        ctlCons.pole_angle = rollAngle

        data["ctlCons"].mute = False
        if data["ikChOf"]:
            data["ikChOf"].mute = True

        ikBone.color.palette = 'THEME04'
# RSTODO 'hide' the pole bone when in FK mode.  (maybe shrink it to near-zero or move it so far off the screen its nearly impossible to find?)
#   (or if we actuall get edit mode to work we can literally delete this bone and recreate it later!)


#######################################################################################################################
def GetAndValidateSelectedBonesForIKConstruction():
    if bpy.context.object and bpy.context.object.mode == 'POSE':  #not necessary as this is only in the pose menu anyway... !!!
        ikBone = bpy.context.active_pose_bone
        if not ikBone or not "_IK" in ikBone.name:
            alertBox("The last bone in selected bones must have '_IK' in its name")
            return None

        selected = [posebone for posebone in bpy.context.object.pose.bones if posebone.bone.select]

        ctlBone = None
        for bone in selected:
            if bone.name == ikBone.name:
                continue                    # skip ourselves

            childBones = []                 # list of children to reparent to ikBone and give 'Copy Location' to
            for child in bone.children:
                if child.name == ikBone.name:
                    # print ("!!FOUND!!")
                    ctlBone = bone
                else:
                    if child in selected:           # only add it if it was a selected bone!
                        childBones.append(child)

            if ctlBone:
                break

        if not ctlBone:
            alertBox("The parent bone of the bone with '_IK' in its name (at a minimum!) must also be selected")
            return None

#RSTODO we don't detect any 'skipping over' of the parent bones and leaving one unselected in the middle of the chain

#found our IK parent bone AND all the children of the _IK bone too!
#now we need to find how many of the selecteds are parents of that IK parent bone!
        count = 1  # always count self
        endBone = ctlBone
        found = True
        while found == True and endBone.parent:
            found = False
            for bone in selected:
#                pdb.set_trace()
                if bone.name == endBone.parent.name:    # found one!  reset and loop again til no more parents!
                    endBone = bone
                    count = count + 1
                    found = True
                    break

        return (ikBone, ctlBone, count, childBones, endBone)
    return None


def MakeIKFrameworkOutOfSelectedBone(withPole):
    import math
    data = GetAndValidateSelectedBonesForIKConstruction()
    if not data: # verify a good selected set of bones and it isn't already IK controlled by them
        return
    
    ikBone,ctlBone,count,childBones,endBone = data  # ikBone, ctlBone, chaincount, childBones and endBone ready to go!

    ebonesRoot = bpy.context.object.data.edit_bones

    ikBoneMatrix = ikBone.matrix.copy() # capture the matrices of bones that get reparented
    cBoneMatrices = []
    for bone in childBones:
        cBoneMatrices.append(bone.matrix.copy())


# step 1, edit mode: create the pole bone
    bpy.ops.object.mode_set(mode='EDIT')

    if withPole:
        poleBone = ebonesRoot.new(name = ctlBone.name + ".IKpole")
        poleBone.head = ctlBone.head    # apparently you have to set the head and tail before the bone actually becomes accessable on switching to POSE Mode
        poleBone.tail = ctlBone.head
        poleBone.tail.y = poleBone.tail.y + 1
        poleBone.use_connect = False
        poleBone.parent = ebonesRoot[endBone.name].parent   # make the endbone of the IKchain the parent of this polebone

# step 2, edit mode: handle all the reparenting
    eIBone = ebonesRoot[ikBone.name]
    for bone in childBones:
        eBone = ebonesRoot[bone.name]
        eBone.use_connect = False
        eBone.parent = eIBone

    eIBone.parent = None

# step 3, pose mode: add the bone constraints
    bpy.ops.object.mode_set(mode='POSE')

    bpy.context.view_layer.update()

    ikBone.matrix = ikBoneMatrix                # restore the matrices
    for idx in range(0, len(childBones)):
        childBones[idx].matrix = cBoneMatrices[idx]

    armature = ikBone.id_data
    for cBone in childBones:
        pBone = armature.pose.bones[cBone.name]
        constraint = pBone.constraints.new(type = "COPY_LOCATION")
        constraint.target = armature
        constraint.subtarget = ctlBone.name
        constraint.head_tail = 1
    
    ikConstraint = ctlBone.constraints.new(type = "IK")
    ikConstraint.target = armature
    ikConstraint.subtarget = ikBone.name
    ikConstraint.chain_count = count

    constraint = ikBone.constraints.new(type = "CHILD_OF")
    constraint.enabled = False
    constraint.target = armature
    constraint.subtarget = ctlBone.name

    ikBone.color.palette = 'THEME04'
    if withPole:
        base_bone = bpy.context.active_object.pose.bones[endBone.name]
        ik_bone = bpy.context.active_object.pose.bones[ctlBone.name]
# script was having 'utf-8' problems when I used poseBone.name (for unknown reasons) so I switched 
# all usage of that to 'ctlBone.name + ".IKpole"' which is the way I named the ctlBone in the first place
#        pdb.set_trace()
        pole_bone = bpy.context.active_object.pose.bones[ctlBone.name + ".IKpole"]

        [poleLoc, rollAngle] = getPoleLocAndAngle(base_bone, ik_bone, pole_bone.matrix.translation)
# these will be needed in the deconstructor
        # poleBone.head = poleLoc.head
        # poleBone.tail = poleLoc.head
        # poleBone.tail.y = poleBone.tail.y + 1

        ikConstraint.pole_target = armature
        ikConstraint.pole_subtarget = ctlBone.name + ".IKpole"
        ikConstraint.pole_angle = rollAngle
        
        # pole_angle_in_deg = round(180*pole_angle_in_radians/3.141592, 3)
        # print(pole_angle_in_deg)

        bpy.context.object.pose.bones[ctlBone.name + ".IKpole"].color.palette = 'THEME11'

# WARNING RSTODO RSFIXME some bones may not be checking for the correct armature as their rootparent!     

def DeleteIKFrameworkfromSelectedBone():
    data = getIKFKControlledBonesFromSelectedIKBone() # get the '_IK' bone and the IK bone
    if not data: # verify a good selected set of bones and it isn't already IK controlled by them
        return

    ikBone = data["ikBone"]
    ctlBone = data["ctlBone"]
    childBones = ikBone.children        # get the children of the '_IK' bone
    poleBone = data["ctlCons"].pole_subtarget  # get name of pole bone for deleting below

    chainCount = data["ctlCons"].chain_count

# step 1, get list of ALL bones that were or may have been affected by this IK
# this skips the pole bone cuz its not parented anywhere inside the affected bones, which is good!!!
    bone = ctlBone
    for count in range(chainCount - 1, 0, -1):  # go up the chain to the first bone affected
        bone = bone.parent

    def getSelfAndKids(bone):
        bones = [bone]
        for child in bone.children:
            bones += getSelfAndKids(child)
        return bones
    allBones = getSelfAndKids(bone)
    allBones += getSelfAndKids(ikBone)

# step 2, make all those bones selected, then apply their transformations
    for bone in allBones:
        bone.bone.select = True
    bpy.ops.pose.visual_transform_apply()   #apply the transformation
    for bone in allBones:
        bone.bone.select = False
    ikBone.bone.select = True  # keep this one selected as it was selected to begin with

# step 4, delete all the constraints directly used by the bones surrounding the '_IK' bone (RSWARN this will delete any we didn't add ourselves)
    constraints = tuple(ikBone.constraints) #copy it to prevent cyclical deletion problems
    for constraint in constraints:
        ikBone.constraints.remove(constraint)

    constraints = tuple(ctlBone.constraints) #copy it to prevent cyclical deletion problems
    for constraint in constraints:
        ctlBone.constraints.remove(constraint)

    for bone in childBones:
        constraints = tuple(bone.constraints) #copy it to prevent cyclical deletion problems
        for constraint in constraints:
            bone.constraints.remove(constraint)

# step 5, edit mode: delete pole bone and reposition and reparent any bones as needed
    ikBoneMatrix = ikBone.matrix.copy()
    cBoneMatrices = []
    for bone in childBones:
        cBoneMatrices.append(bone.matrix.copy())

    bpy.ops.object.mode_set(mode='EDIT')

    ebonesRoot = bpy.context.object.data.edit_bones
    if poleBone:
        ebonesRoot.remove(ebonesRoot[poleBone])     # remove pole bone outright!

    for bone in childBones:                 # now reparent the children of '_IK' to the ctlBone
        eBone = ebonesRoot[bone.name]
        eBone.parent = ebonesRoot[ctlBone.name]   # move any controlled afterbones back onto the controlled bone
        eBone.use_connect = True

    eBone = ebonesRoot[ikBone.name]               # now set the '_IK' bones parent back to the controlled bone too
    eBone.parent = ebonesRoot[ctlBone.name]
    eBone.use_connect = True

#step 6, pose mode: restore the matrices and clear the color of the '_IK' bone
    bpy.ops.object.mode_set(mode='POSE')
    ikBone.matrix = ikBoneMatrix
    for idx in range(0, len(childBones)):
        childBones[idx].matrix = cBoneMatrices[idx]

    ikBone.color.palette = "DEFAULT"

def prt(name, vec):
    print(name,"=",vec.x,",",vec.y,",",vec.z)

def getPoleLocAndAngle(endBone, ctlBone, pole_location):
    # prt("endbone head", endBone.head)
    # prt("endbone tail", endBone.tail)
    # print("endbone x_axis=", endBone.x_axis)
    # prt("ctlbone.tail", ctlBone.tail)
    # prt("pole_location", pole_location)
    # print()

    def signed_angle(vector_u, vector_v, normal):
        angle = vector_u.angle(vector_v)
        if vector_u.cross(vector_v).angle(normal) < 1:
            angle = -angle
        return angle
    pole_normal = (ctlBone.tail - endBone.head).cross(pole_location - endBone.head)
    projected_pole_axis = pole_normal.cross(endBone.tail - endBone.head)
    return [pole_location, signed_angle(endBone.x_axis, projected_pole_axis, endBone.tail - endBone.head)]


#######################################################################################################################
#######################################################################################################################
#######################################################################################################################
def makeData():
    return {
        "ikBone"  : None,   # wrist_IK.l  ... the selected '_IK' bone itself
        "ikChOf"  : None,   # ChldOfCnst  ... constraint on '_IK' bone, Target="arm.L.002"
        "ctlBone" : None,   # arm.L.002   ... bone just above '_IK' bone that has the actual IK constraint on it
        "ctlCons" : None,   # IKconstrnt  ... Target="wrist_IK.L", pole="IK_pole_elbow.L"
    }


def getIKFKControlledBonesFromSelectedIKBone():
    ikBone = getSelectedIKBone()                         # 'wrist_IK.l'
    if ikBone:
        data = makeData()

        for constraint in ikBone.constraints:               # get the 'CHILD_OF' constraint (if present)
            if constraint.type == "CHILD_OF":
                data["ikChOf"] = constraint

        ikBone = data["ikBone"] = getSelectedIKBone()                         # 'wrist_IK.l'
        cBoneInfo = getIKConstrainingBone(ikBone.name)   # ['arm.L.002', IKconstraint(targetBone='wrist_IK.l'])
        if cBoneInfo:    # *** select all bones in the IK's chain length, apply visual transform, then set influence to 0 ***
            posebone,constraint = [data["ctlBone"], data["ctlCons"]] = cBoneInfo
            # print("Looking from " + ikBone.name + ", Found bone named " + posebone.name)
            # print("BoneCount in chain = ",constraint.chain_count)
        return data
    return None


def getIKConstrainingBone(boneName):
    # print("bname=",boneName)
    obj = bpy.context.object
    bones = obj.pose.bones    # get the pose bones
    for posebone in bones:
        for constraint in posebone.constraints:
            if constraint.type == "IK":
                # print("cname=",constraint.name)
                # print("influence=",constraint.influence)
                # print("poletarget", constraint.pole_target.name)
                # print("polesubtarget=",constraint.pole_subtarget)
                # print("target=",constraint.target.name)
                # print("targetbone=",constraint.subtarget)
                if constraint.subtarget == boneName:
                    return [posebone, constraint]
    return None



def getSelectedIKBone():
    if bpy.context.object and bpy.context.object.mode == 'POSE':  # or 'EDIT' or 'OBJECT'
        obj = bpy.context.object
#        bones = obj.data.bones        # get the armature data
        bones = obj.pose.bones    # get the pose bones

        selected = [posebone for posebone in bones if posebone.bone.select]

        if len(selected) == 1 and "_IK" in selected[0].name:
                return selected[0]
    alertBox("The bone with '_IK' in its name must be selected")
    return None


#######################################################################################################################
#######################################################################################################################
#######################################################################################################################
def alertBox(msg):
    def draw(self, context):
        self.layout.label(text = msg)
    bpy.context.window_manager.popup_menu(draw, title = "Error", icon = 'ERROR')


class IKFKMenuOperator(bpy.types.Operator):
# bl_idname cant start with a capital letter and must have a '.' in it, doesnt seem to care otherwise
    bl_idname = "mymenuopclass.mycustom_operator"
    bl_label = "Custom Operator"

    action: bpy.props.StringProperty()

    def execute(self, context):
        if self.action == "IKtoFK":
            IK_to_FK()
        elif self.action == "FKtoIK":
            FK_to_IK()
        elif self.action == "MakeIKWithPole":
            MakeIKFrameworkOutOfSelectedBone(True)
        elif self.action == "MakeIKWithoutPole":
            MakeIKFrameworkOutOfSelectedBone(False)
        elif self.action == "DeleteIK":
            DeleteIKFrameworkfromSelectedBone()
        elif self.action == "Breaker19!":
            breaker19()


        return {'FINISHED'}


class IKFKMenu(bpy.types.Menu):
    bl_idname = "OBJECT_MT_ikfi_mymenu"
    bl_label = "IK-FK Switcher"

    def draw(self, context):
        self.layout.operator("mymenuopclass.mycustom_operator", text = "IK to FK").action = "IKtoFK"
        self.layout.operator("mymenuopclass.mycustom_operator", text = "FK to IK").action = "FKtoIK"
        self.layout.separator()
        self.layout.operator("mymenuopclass.mycustom_operator", text = "Create IK Assembly").action = "MakeIKWithPole"
# this next line works fine, but we don't really need it
#        self.layout.operator("mymenuopclass.mycustom_operator", text = "Create IK Assembly without Pole Bone").action = "MakeIKWithoutPole"
        self.layout.separator()
        self.layout.operator("mymenuopclass.mycustom_operator", text = "Delete IK Assembly").action = "DeleteIK"
        # self.layout.separator()
        # self.layout.operator("mymenuopclass.mycustom_operator", text = "Breaker 1-9!").action = "Breaker19!"


def draw_IKFKMenu(self, context):
    self.layout.menu(IKFKMenu.bl_idname)

def register():
    menu = bpy.types.VIEW3D_MT_pose    # 3D viewport's 'Pose Mode-->Pose' menu
#    menu = bpy.types.VIEW3D_MT_object  # 3D viewport's 'Object Mode-->Object' menu
    bpy.utils.register_class(IKFKMenuOperator)
    bpy.utils.register_class(IKFKMenu)
    menu.append(draw_IKFKMenu)

def unregister():   # new way that iters through objects and compares each instanced function's name to the real funcs name to remove them that way instead
    menu = bpy.types.VIEW3D_MT_pose    # 3D viewport's 'Pose Mode-->Pose' menu
#    menu = bpy.types.VIEW3D_MT_object  # 3D viewport's 'Object Mode-->Object' menu
    found = True
    while found:       # we loop in this way to get rid of multiple names
        found = False
        for f in menu._dyn_ui_initialize():
            # print(f.__name__, draw_IKFKMenu.__name__)
            if f.__name__ == draw_IKFKMenu.__name__:
                # print("removing...")
                menu.remove(f)
                found = True
                break
    try:
        bpy.utils.unregister_class(IKFKMenu)    # these tend to throw an error so lets just try-trap it
    except:
        pass
    try:
        bpy.utils.unregister_class(IKFKMenuOperator)
    except:
        pass

unregister()
if __name__ == "__main__":
    register()

