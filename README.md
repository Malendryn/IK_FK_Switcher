# IK_FK_Switcher
A 'simple as one click!' way to add entire IK chains, pose them, switch between IK and FK, and if desired, remove them

I mean that quite literally,  this script does the following:
1) select all the bones that make up an IK chain, including the bones that you want to come right after the posing bone (the one you drag around) and in one click, it builds the entire IK chain, including the pole bone!
2) Immediately start using the IK chain by dragging the control or pole bones around like you normally would.
3) Switch from IK to FK with another single click! and back again!
4) Delete all the elements that were added to you bone structure and return it to a fully pre-IK chain!

Right now the 'one-click' is done through the Pose menu dropdown, but if there is any interest in this I can add this as a sidebar option as well.  (right now I use it by attaching these to the quick favorites popup which is just as convenient to me.)

The download is just a single .blend file, which is set up with all the right bones selected and the only specially-named bone (a bone with '_IK' somewhere in its name) as the last bone in the selection list.

All you have to do once the .blend file is loaded is (first!) run the script in the text window at the bottom (it is not yet setup as an actual add-on either)

And then in the Pose menu at the bottom choose 'Pose->IK-FK Switcher->Create IK Assembly'

The rest is pretty self explanatory!
