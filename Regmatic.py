from __main__ import vtk, qt, ctk, slicer
from array import array

import math, time
import numpy as np
import numpy as numpy
import vtk.util.numpy_support as vtk_np
#
# Regmatic
#

class Regmatic:
  def __init__(self, parent):
    parent.title = "Regmatic"
    parent.categories = ["Registration"]
    parent.dependencies = []
    parent.contributors = ["Steve Pieper (Isomics)"] # replace with "Firstname Lastname (Org)"
    parent.helpText = """
    Steerable registration example as a scripted loadable extension.
    """
    parent.acknowledgementText = """
    This file was originally developed by Steve Pieper and was partially funded by NIH grant 3P41RR013218.
""" # replace with organization, grant and thanks.
    self.parent = parent

#
# qRegmaticWidget
#

class RegmaticWidget:
  def __init__(self, parent = None):
    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
    else:
      self.parent = parent
    self.layout = self.parent.layout()
    if not parent:
      self.setup()
      self.parent.show()

    self.logic = RegmaticLogic()


  def setup(self):
    # Instantiate and connect widgets ...

    # reload button
    self.reloadButton = qt.QPushButton("Reload")
    self.reloadButton.toolTip = "Reload this module."
    self.reloadButton.name = "Regmatic Reload"
    self.layout.addWidget(self.reloadButton)
    self.reloadButton.connect('clicked()', self.onReload)

    #
    # io Collapsible button
    #
    ioCollapsibleButton = ctk.ctkCollapsibleButton()
    ioCollapsibleButton.text = "Volume and Transform Parameters"
    self.layout.addWidget(ioCollapsibleButton)

    # Layout within the parameter collapsible button
    ioFormLayout = qt.QFormLayout(ioCollapsibleButton)

    # Fixed Volume node selector
    self.fixedSelector = slicer.qMRMLNodeComboBox()
    self.fixedSelector.objectName = 'fixedSelector'
    self.fixedSelector.toolTip = "The fixed volume."
    self.fixedSelector.nodeTypes = ['vtkMRMLScalarVolumeNode']
    self.fixedSelector.noneEnabled = False
    self.fixedSelector.addEnabled = False
    self.fixedSelector.removeEnabled = False
    ioFormLayout.addRow("Fixed Volume:", self.fixedSelector)
    self.fixedSelector.setMRMLScene(slicer.mrmlScene)
    self.parent.connect('mrmlSceneChanged(vtkMRMLScene*)',
                        self.fixedSelector, 'setMRMLScene(vtkMRMLScene*)')

    # Moving Volume node selector
    self.movingSelector = slicer.qMRMLNodeComboBox()
    self.movingSelector.objectName = 'movingSelector'
    self.movingSelector.toolTip = "The moving volume."
    self.movingSelector.nodeTypes = ['vtkMRMLScalarVolumeNode']
    self.movingSelector.noneEnabled = False
    self.movingSelector.addEnabled = False
    self.movingSelector.removeEnabled = False
    ioFormLayout.addRow("Moving Volume:", self.movingSelector)
    self.movingSelector.setMRMLScene(slicer.mrmlScene)
    self.parent.connect('mrmlSceneChanged(vtkMRMLScene*)',
                        self.movingSelector, 'setMRMLScene(vtkMRMLScene*)')
                        
    # Fiducial node selector
    self.__fiducialSelector = slicer.qMRMLNodeComboBox()
    self.__fiducialSelector.objectName = 'fiducialSelector'
    self.__fiducialSelector.toolTip = "The fiducial."
    self.__fiducialSelector.nodeTypes = ['vtkMRMLAnnotationFiducialNode']
    self.__fiducialSelector.noneEnabled = False
    self.__fiducialSelector.addEnabled = False
    self.__fiducialSelector.removeEnabled = False
    ioFormLayout.addRow("Fiducial:", self.__fiducialSelector)
    self.__fiducialSelector.setMRMLScene(slicer.mrmlScene)
    self.parent.connect('mrmlSceneChanged(vtkMRMLScene*)',
                        self.__fiducialSelector, 'setMRMLScene(vtkMRMLScene*)')
                        
    #check button for moving rotation point
    self.__moverotCenterButton = qt.QCheckBox()
    self.__moverotCenterButton.setEnabled(1)
    moverotLabel = qt.QLabel('Define fiducial point as rotation center')
    ioFormLayout.addRow(moverotLabel, self.__moverotCenterButton)
    self.__moverotCenterButton.connect('stateChanged(int)', self.updateLogicFromGUI)

    # Transform node selector
    self.transformSelector = slicer.qMRMLNodeComboBox()
    self.transformSelector.objectName = 'transformSelector'
    self.transformSelector.toolTip = "The transform volume."
    self.transformSelector.nodeTypes = ['vtkMRMLLinearTransformNode']
    self.transformSelector.noneEnabled = False
    self.transformSelector.addEnabled = False
    self.transformSelector.removeEnabled = False
    ioFormLayout.addRow("Moving To Fixed Transform:", self.transformSelector)
    self.transformSelector.setMRMLScene(slicer.mrmlScene)
    self.parent.connect('mrmlSceneChanged(vtkMRMLScene*)',
                        self.transformSelector, 'setMRMLScene(vtkMRMLScene*)')
    selectors = (self.fixedSelector, self.movingSelector, self.transformSelector,self.__fiducialSelector)
    for selector in selectors:
      selector.connect('currentNodeChanged(vtkMRMLNode*)', self.updateLogicFromGUI)

    #
    # opt Collapsible button
    #
    optCollapsibleButton = ctk.ctkCollapsibleButton()
    optCollapsibleButton.text = "Optimizer Parameters"
    self.layout.addWidget(optCollapsibleButton)

    # Layout within the parameter collapsible button
    optFormLayout = qt.QFormLayout(optCollapsibleButton)

    # gradient window slider
    self.sampleSpacingSlider = ctk.ctkSliderWidget()
    self.sampleSpacingSlider.decimals = 2
    self.sampleSpacingSlider.singleStep = 0.01
    self.sampleSpacingSlider.minimum = 0.01
    self.sampleSpacingSlider.maximum = 100
    self.sampleSpacingSlider.toolTip = "Multiple of spacing used when extracting pixels to evaluate objective function"
    optFormLayout.addRow("Sample Spacing:", self.sampleSpacingSlider)

    # gradient window slider
    self.gradientWindowSlider = ctk.ctkSliderWidget()
    self.gradientWindowSlider.decimals = 2
    self.gradientWindowSlider.singleStep = 0.01
    self.gradientWindowSlider.minimum = 0.01
    self.gradientWindowSlider.maximum = 5
    self.gradientWindowSlider.toolTip = "Multiple of spacing used when estimating objective function gradient"
    optFormLayout.addRow("Gradient Window:", self.gradientWindowSlider)

    # step size slider
    self.stepSizeSlider = ctk.ctkSliderWidget()
    self.stepSizeSlider.decimals = 2
    self.stepSizeSlider.singleStep = 0.01
    self.stepSizeSlider.minimum = 0.01
    self.stepSizeSlider.maximum = 20
    self.stepSizeSlider.toolTip = "Multiple of spacing used when taking an optimization step"
    optFormLayout.addRow("Rotation Step Size:", self.stepSizeSlider)

    # get default values from logic
    self.sampleSpacingSlider.value = self.logic.sampleSpacing
    self.gradientWindowSlider.value = self.logic.gradientWindow
    self.stepSizeSlider.value = self.logic.stepSize

    sliders = (self.sampleSpacingSlider, self.gradientWindowSlider, self.stepSizeSlider)
    for slider in sliders:
      slider.connect('valueChanged(double)', self.updateLogicFromGUI)
   

    # Run button
    self.runButton = qt.QPushButton("Interaction")
    self.runButton.toolTip = "Run registration bot."
    self.runButton.checkable = True
    optFormLayout.addRow(self.runButton)
    self.runButton.connect('toggled(bool)', self.onRunButtonToggled)
     # Optimize button
    self.optimizeButton = qt.QPushButton("Optimize Translation")
    self.optimizeButton.toolTip = "Run optimization."
    self.optimizeButton.checkable = True
    optFormLayout.addRow(self.optimizeButton)
    self.optimizeButton.connect('toggled(bool)', self.onOptimizeButtonToggled)
    # Optimize Rotation button
    self.optimizeRotationButton = qt.QPushButton("Optimize Rotation")
    self.optimizeRotationButton.toolTip = "Run optimization."
    self.optimizeRotationButton.checkable = True
    optFormLayout.addRow(self.optimizeRotationButton)
    self.optimizeRotationButton.connect('toggled(bool)', self.onOptimizeRotationButtonToggled)

    # to support quicker development:
    import os
    if os.getenv('USERNAME') == 'guillaume' or os.getenv('USERNAME') == 'Guillaume':
      self.logic.testingData()
      self.fixedSelector.setCurrentNode(slicer.util.getNode('MRHead*'))
      self.movingSelector.setCurrentNode(slicer.util.getNode('neutral*'))
      self.transformSelector.setCurrentNode(slicer.util.getNode('movingToFixed*'))

    # Add vertical spacer
    self.layout.addStretch(1)

  def updateLogicFromGUI(self,args):
    self.logic.fixed = self.fixedSelector.currentNode()
    self.logic.moving = self.movingSelector.currentNode()
    self.logic.transform = self.transformSelector.currentNode()
    self.logic.fiducial = self.__fiducialSelector.currentNode()
    self.logic.checked = self.__moverotCenterButton
    self.logic.sampleSpacing = self.sampleSpacingSlider.value
    self.logic.gradientWindow = self.gradientWindowSlider.value
    self.logic.stepSize = self.stepSizeSlider.value

  def onRunButtonToggled(self, checked):
    if checked:
      self.logic.start()
      self.runButton.text = "Stop"
    else:
      self.logic.stop()
      self.runButton.text = "Interaction"

  def onOptimizeButtonToggled(self,checked):
    if checked:  
      self.logic.startRegistration()
      self.optimizeButton.text = "Processing"
    else:
      self.logic.stopRegistration()
      self.optimizeButton.text = "Translation Optimization"
      
  def onOptimizeRotationButtonToggled(self,checked):
    if checked:  
      self.logic.startRegistrationRotation(self.logic.stepSize)
      self.optimizeRotationButton.text = "Processing"
    else:
      self.logic.stopRegistrationRotation()
      self.optimizeRotationButton.text = "Rotation Optimization"
      
  def onReload(self,moduleName="Regmatic"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    """
    import imp, sys, os, slicer

    widgetName = moduleName + "Widget"

    # reload the source code
    # - set source file path
    # - load the module to the global space
    filePath = eval('slicer.modules.%s.path' % moduleName.lower())
    p = os.path.dirname(filePath)
    if not sys.path.__contains__(p):
      sys.path.insert(0,p)
    fp = open(filePath, "r")
    globals()[moduleName] = imp.load_module(
        moduleName, fp, filePath, ('.py', 'r', imp.PY_SOURCE))
    fp.close()

    # rebuild the widget
    # - find and hide the existing widget
    # - create a new widget in the existing parent
    parent = slicer.util.findChildren(name='%s Reload' % moduleName)[0].parent()
    for child in parent.children():
      try:
        child.hide()
      except AttributeError:
        pass
    globals()[widgetName.lower()] = eval(
        'globals()["%s"].%s(parent)' % (moduleName, widgetName))
    globals()[widgetName.lower()].setup()

#
# Regmatic logic
#

class RegmaticLogic(object):
  """ Implement a template matching optimizer that is
  integrated with the slicer main loop.
  Note: currently depends on numpy/scipy installation in mac system
  """

  def __init__(self,fixed=None,moving=None,transform=None,fiducial=None,checked = None):
    self.interval = 2
    self.timer = None

    # parameter defaults
    self.sampleSpacing = 10
    self.gradientWindow = 1
    self.stepSize = 1

    # slicer nodes set by the GUI
    self.fixed = fixed
    self.moving = moving
    self.transform = transform
    self.fiducial = fiducial
    self.checked = checked

    # optimizer state variables
    self.iteration = 0
    self.position = [0, 0, 0]
    self.paintCoordinates = []
    self.x0, self.y0, self.z0 = 0,0,0
    self.tx0, self.ty0,self.tz0 = 0,0,0   
    self.m = vtk.vtkMatrix4x4()
    self.r = vtk.vtkTransform()
    self.transformNode,self.neutral = None, None
    self.before = 0
    self.plan = 'plan'  
    self.actionState = "idle"
    self.interactorObserverTags = []    
    self.styleObserverTags = []
    self.sliceWidgetsPerStyle = {}
    self.tac=0
    self.WMAX = 0
    self.L=[]
    self.divider = 1
    self.step = 1

    # helper objects
    self.scratchMatrix = vtk.vtkMatrix4x4()
    self.ijkToRAS = vtk.vtkMatrix4x4()
    self.rasToIJK = vtk.vtkMatrix4x4()
    self.reslice = vtk.vtkImageReslice()
    self.resliceTransform = vtk.vtkTransform()
    self.viewer = None
    self.render = None
    #self.weightmax = 400000
   
  def start(self):
    
    self.removeObservers()
    # get new slice nodes
    layoutManager = slicer.app.layoutManager()
    sliceNodeCount = slicer.mrmlScene.GetNumberOfNodesByClass('vtkMRMLSliceNode')
    for nodeIndex in xrange(sliceNodeCount):
      # find the widget for each node in scene
      sliceNode = slicer.mrmlScene.GetNthNodeByClass(nodeIndex, 'vtkMRMLSliceNode')
      sliceWidget = layoutManager.sliceWidget(sliceNode.GetLayoutName())      
      if sliceWidget:     
        # add obserservers and keep track of tags
        style = sliceWidget.sliceView().interactorStyle()
        self.sliceWidgetsPerStyle[style] = sliceWidget
        events = ("LeftButtonPressEvent","LeftButtonReleaseEvent","MouseMoveEvent", "KeyPressEvent","KeyReleaseEvent","EnterEvent", "LeaveEvent")
        for event in events:
          tag = style.AddObserver(event, self.processEvent)
   
          self.styleObserverTags.append([style,tag])
  def startRegistration(self):
    """Create the subprocess and set up a polling timer"""
    if self.timer:
      self.stop()
    self.timer = qt.QTimer()
    self.timer.setInterval(self.interval)
    self.timer.connect('timeout()', self.registration)
    self.timer.start()

  def startRegistrationRotation(self,step = None):
    """Create the subprocess and set up a polling timer"""
    self.step = step
    if self.timer:
      self.stop()
    self.timer = qt.QTimer()
    self.timer.setInterval(self.interval)
    self.timer.connect('timeout()', self.registrationRotation)
    self.timer.start()
    
  def stopRegistration(self):
    if self.timer:
      self.timer.stop()
      self.timer = None
      self.L=[]
      self.divider= float(1)
      
  def stopRegistrationRotation(self):
    if self.timer:
      self.timer.stop()
      self.timer = None
      self.L=[]
      self.divider= float(1)
          
  def processEvent(self,observee,event=None):

    ######################################  transformation  ##########################
    
    if self.sliceWidgetsPerStyle.has_key(observee):
      sliceWidget = self.sliceWidgetsPerStyle[observee]
      style = sliceWidget.sliceView().interactorStyle()

      if event == "KeyPressEvent":
        key = style.GetInteractor().GetKeySym()
        if key == 'a' and self.actionState != "translation":
          self.actionState = "translation"          
        elif key == 's' and self.actionState != "rotation":
          self.actionState = "rotation"
        elif key == 's' and self.actionState == "rotation":
          self.actionState = "idle"
          self.before = 0
        elif key == 'a' and self.actionState == "translation":
          self.actionState = "idle"
          self.before = 0
      #if event =='KeyReleaseEvent':
       # self.oldtime = time.time()
      #if time.time() - self.oldtime > 0.120:
      #  self.actionState = "idle"
      #  self.before = 0
      print(self.actionState)

      global fi, theta, psi
      
      if (self.actionState == "rotation" or self.actionState == "translation"):

        ############################  rotation ########################################
        if self.actionState == "rotation" and event == "MouseMoveEvent":
          xy = style.GetInteractor().GetEventPosition()
          xyz = sliceWidget.convertDeviceToXYZ(xy)
          ras = sliceWidget.convertXYZToRAS(xyz)
          tx = 0
          ty = 0
          tz = 0
          fi=0
          theta = 0
          psi = 0
          x = ras[0]
          y = ras[1]
          z = ras[2]
          self.r = vtk.vtkTransform()
          if self.before == 0:
            self.x0 = ras[0]
            self.y0 = ras[1]
            self.z0 = ras[2]
            self.tx0 = self.m.GetElement(0,3)
            self.ty0 = self.m.GetElement(1,3)
            self.tz0 = self.m.GetElement(2,3)      
            if y == 0:
              self.plan = 'yplan'      
            elif z == 0:
              self.plan = 'zplan'
            elif x == 0:
              self.plan = 'xplan'
          tx = x - self.x0
          ty = y - self.y0
          tz = z - self.z0

          self.m =  self.transform.GetMatrixTransformToParent()
          global center, new_rot_point, mouv_mouse
          center = [0,0,0]
          #################### rotation with fiducial point as center: translation ° rotation ° (-translation) ####################
          print(self.checked)
          if self.fiducial and self.checked.isChecked() :
            # fiducialNode = slicer.util.getNode('vtkMRMLAnnotationFiducialNode1')
            # fiducialNode.GetFiducialCoordinates(center)
            self.fiducial.GetFiducialCoordinates(center)
            new_rot_point = [center[0]-self.tx0,center[1]-self.ty0,center[2]-self.tz0]
            translate_back = [k * -1 for k in new_rot_point]    
            mouv_mouse=[tx,ty,tz]
            self.r.Translate(new_rot_point)
            if self.plan == 'yplan':
              self.r.RotateWXYZ(tx,0,1,0)         
            elif self.plan == 'zplan':
              #self.r.RotateZ(tx)
              self.r.RotateWXYZ(tx,0,0,1)  
            elif self.plan == 'xplan':
              #self.r.RotateX(ty)
              self.r.RotateWXYZ(ty,1,0,0)
            self.r.Translate(translate_back)  
            self.transform.ApplyTransformMatrix(self.r.GetMatrix())       
            self.x0 = x
            self.y0 = y
            self.z0 = z
          #################### rotation without fiducial point as center #########################################################
          else:
            new_rot_point = [self.tx0,self.ty0,self.tz0]
            translate_back = [k * -1 for k in new_rot_point]    
            mouv_mouse=[tx,ty,tz]
            self.r.Translate(new_rot_point)
            if self.plan == 'yplan':
              self.r.RotateWXYZ(tx,0,1,0)         
            elif self.plan == 'zplan':
              #self.r.RotateZ(tx)
              self.r.RotateWXYZ(tx,0,0,1)  
            elif self.plan == 'xplan':
              #self.r.RotateX(ty)
              self.r.RotateWXYZ(ty,1,0,0)
            self.r.Translate(translate_back)  
            self.transform.ApplyTransformMatrix(self.r.GetMatrix())       
            self.x0 = x
            self.y0 = y
            self.z0 = z
          
          
          self.before += 1

        ######################################### translation ###########################################
        elif self.actionState == "translation" and event == "MouseMoveEvent":
          xy = style.GetInteractor().GetEventPosition()
          xyz = sliceWidget.convertDeviceToXYZ(xy);
          ras = sliceWidget.convertXYZToRAS(xyz)
          x = ras[0]
          y = ras[1]
          z = ras[2]
          self.m = self.transform.GetMatrixTransformToParent()
          if self.before == 0:
            self.x0 = ras[0]
            self.y0 = ras[1]
            self.z0 = ras[2]
            self.tx0 = self.m.GetElement(0,3)
            self.ty0 = self.m.GetElement(1,3)
            self.tz0 = self.m.GetElement(2,3)  
          tx = x - self.x0 
          ty = y - self.y0 
          tz = z - self.z0
          self.translate(self.tx0+tx,self.ty0+ty,self.tz0+tz)
          
          self.before += 1
       
        self.colorWindow()

  def tick(self):

    movingRASArray = self.rasArray(self.moving, None, self.fixed)
    fixedRASArray = self.rasArray(self.fixed, None, self.fixed)
    weight = numpy.sum(numpy.abs(movingRASArray-fixedRASArray))
  
    return(weight)

  def weightMax(self):
  
    movingRASArray = self.rasArray(self.moving, None, self.fixed)
    fixedRASArray = self.rasArray(self.fixed, None, self.fixed)
    wmax = numpy.max(([numpy.sum(movingRASArray),numpy.sum(fixedRASArray)]))
  
    return(wmax)

  def rasArray(self, volumeNode, matrix=None, targetNode=None, debug=True):
    """
    Returns a numpy array of the given node resampled into RAS space
    If given, use the passed matrix as a final RAS to RAS transform
    """

    # get the transform from image space to world space
    volumeNode.GetIJKToRASMatrix(self.ijkToRAS)
    transformNode = volumeNode.GetParentTransformNode()
    if transformNode:
      self.scratchMatrix.Identity()
      transformNode.GetMatrixTransformToWorld(self.scratchMatrix)
      self.ijkToRAS.Multiply4x4(self.scratchMatrix, self.ijkToRAS, self.ijkToRAS)

    if matrix:
      self.ijkToRAS.Multiply4x4(matrix, self.ijkToRAS, self.ijkToRAS)

    self.rasToIJK.DeepCopy(self.ijkToRAS)
    self.rasToIJK.Invert()

    # use the matrix to extract the volume and convert it to an array
    self.reslice.SetInterpolationModeToLinear()
    self.reslice.InterpolateOn()
    self.resliceTransform.SetMatrix(self.rasToIJK)
    self.reslice.SetResliceTransform(self.resliceTransform)
    # TODO: set the dimensions and spacing
    #self.reslice.SetInformationInput( nodes[template_name].GetImageData() )
    self.reslice.SetInput( volumeNode.GetImageData() )
    self.reslice.UpdateWholeExtent()
    rasImage = self.reslice.GetOutput()
    shape = list(rasImage.GetDimensions())
    shape.reverse()
    rasArray = vtk.util.numpy_support.vtk_to_numpy(rasImage.GetPointData().GetScalars()).reshape(shape)

    if targetNode:
      bounds = [0,]*6
      targetNode.GetRASBounds(bounds)
      self.reslice.SetOutputExtent(0, (bounds[1]-bounds[0])/self.sampleSpacing,
                                   0, (bounds[3]-bounds[2])/self.sampleSpacing,
                                   0, (bounds[5]-bounds[4])/self.sampleSpacing)
      self.reslice.SetOutputOrigin(bounds[0],bounds[2],bounds[4])

    self.reslice.SetOutputSpacing([self.sampleSpacing,]*3)

    return rasArray

  def colorWindow(self):
    if not self.viewer:
      self.viewer = vtk.vtkRenderWindow()
      self.render= vtk.vtkRenderer()
    ratio,red,green = 0,0,0
    ratio = self.tick()/float(self.weightMax())
    red = ratio
    green = 1-ratio
    self.render.SetBackground(red,green,0)   
    self.viewer.AddRenderer(self.render)
    self.viewer.Render()  

  def stop(self):
    self.actionState = "idle"
    print("here")
    self.removeObservers()   

  def removeObservers(self):
    # remove observers and reset
    for observee,tag in self.styleObserverTags:
      observee.RemoveObserver(tag)
    self.styleObserverTags = []
    self.sliceWidgetsPerStyle = {}
        
  def translate(self,x,y,z):
    self.m.SetElement(0,3,x)
    self.m.SetElement(1,3,y)
    self.m.SetElement(2,3,z)

  def rotate(self,fi,theta,psi):
    self.tx0 = self.m.GetElement(0,3)
    self.ty0 = self.m.GetElement(1,3)
    self.tz0 = self.m.GetElement(2,3)
    self.r = vtk.vtkTransform()
    self.r.Translate([self.tx0,self.ty0,self.tz0])
    #self.r.Translate(new_rot_point)
    self.r.RotateWXYZ(theta,0,1,0)         
    self.r.RotateWXYZ(psi,0,0,1)  
    self.r.RotateWXYZ(fi,1,0,0)
    self.r.Translate([-self.tx0,-self.ty0,-self.tz0])  
    self.transform.ApplyTransformMatrix(self.r.GetMatrix()) 
  
  def rotateRegistrationX(self,fiStep,nbIteration):
    ######################## rotation X axis ############################################
    #print("before iteration" , self.tick())
    fiBestValue,fiBestMove = self.tick(), 0
    for fi in xrange(1,nbIteration+1):
      self.rotate(fiStep,0,0)
      if self.tick() < fiBestValue:
        fiBestValue = self.tick()
        fiBestMove = fi
        self.colorWindow()
        print("fi", fi , fiBestValue)
    if fiBestMove == 0:                         
      self.rotate(-fiStep*(nbIteration),0,0)
    else:
      self.rotate(fiStep*(fiBestMove - nbIteration),0,0)
    #print("after iteration",self.tick())
    print("fi", fiBestMove , fiBestValue)
    
  def rotateRegistrationY(self,thetaStep,nbIteration):  
    #################### rotation Y axis #########################################
    #print("before iteration" , self.tick())
    thetaBestValue,thetaBestMove = self.tick(), 0
    for theta in xrange(1,nbIteration+1):
      self.rotate(0,thetaStep,0)
      if self.tick() < thetaBestValue:
        thetaBestValue = self.tick()
        thetaBestMove = theta
        self.colorWindow()
        print("theta", theta , thetaBestValue)
    if thetaBestMove == 0:                         
      self.rotate(0,-thetaStep*(nbIteration),0)
    else:
      self.rotate(0,thetaStep*(thetaBestMove - nbIteration),0)
    #print("after iteration",self.tick())
    print("theta", thetaBestMove , thetaBestValue)
  
  def rotateRegistrationZ(self,psiStep,nbIteration): 
    #################### rotation Z axis ########################################
    #print("before iteration" , self.tick())
    psiBestValue,psiBestMove = self.tick(), 0
    for psi in xrange(1,nbIteration+1):
      self.rotate(0,0,psiStep)
      if self.tick() < psiBestValue:
        psiBestValue = self.tick()
        psiBestMove = psi
        self.colorWindow()
        print("psi", psi , psiBestValue)
    if psiBestMove == 0:                         
      self.rotate(0,0,-psiStep*(nbIteration))
    else:
      self.rotate(0,0,psiStep*(psiBestMove - nbIteration))
    #print("after iteration",self.tick())
    print("psi", psiBestMove , psiBestValue)
      
  def translateRegistration(self,iMax,jMax,kMax,iStep,jStep,kStep):
    self.tx0 = self.m.GetElement(0,3)
    self.ty0 = self.m.GetElement(1,3)
    self.tz0 = self.m.GetElement(2,3)
    self.WMAX = self.weightMax()
    iBestValue,iBestMove = 2*self.WMAX,0
    jBestValue,jBestMove = 2*self.WMAX,0
    kBestValue,kBestMove = 2*self.WMAX,0
    fiBestValue,fiBestMove = 2*self.WMAX,0
    theta_bestValue,theta_bestMove = 2*self.WMAX,0
    psiBestValue,psiBestMove = 2*self.WMAX,0
    
    total = 2*(iMax+jMax+kMax)-6
    for i in xrange(-iMax,iMax):
      self.translate(self.tx0+i*iStep,self.ty0,self.tz0)
      if self.tick() <= iBestValue:
        iBestValue = self.tick()
        iBestMove = i*iStep
        self.colorWindow()
    for j in xrange(-jMax,jMax):
      self.translate(self.tx0+ iBestMove,self.ty0+j*jStep,self.tz0)
      if self.tick() <= jBestValue:
        jBestValue = self.tick()
        jBestMove = j*jStep
        self.colorWindow()
    for k in xrange(-kMax,kMax):
      self.translate(self.tx0 + iBestMove , self.ty0 + jBestMove , self.tz0 + k*kStep)
      if self.tick() <= kBestValue:
        kBestValue = self.tick()
        kBestMove = k*kStep
        self.colorWindow()
    self.translate(-iMax*iStep + self.tx0,-jMax*jStep + self.ty0,-kMax*kStep + self.tz0)
    self.translate(iBestMove + self.tx0 , jBestMove + self.ty0 , kBestMove + self.tz0)
    print(self.tick())
    


  def registration(self):
    self.L.append(self.tick())
    #print("L",self.L)
    if self.L[-1] == self.L[-2]:
      self.divider *= float(2)
    else:
      self.divider *= float(1)
    self.WMAX = self.weightMax()
    iStep = max([int((self.tick()/float(self.WMAX))**2*15),0.1])
    print("istep",iStep)
    self.translateRegistration(10,0,0,iStep/self.divider,1,1)
    jStep = max([int((self.tick()/float(self.WMAX))**2*15),0.1])
    print("jstep",jStep)
    self.translateRegistration(0,10,0,1,jStep/self.divider,1)
    kStep = max([int((self.tick()/float(self.WMAX))**2*15),0.1])
    print("kstep",kStep)
    self.translateRegistration(0,0,10,1,1,kStep/self.divider)

    print(self.tick())
    self.colorWindow()
    
  def registrationRotation(self):
    self.WMAX = self.weightMax()
    
    self.step = min([max([(self.tick()/float(self.WMAX))**2*15,0.01]),self.step])
    print("stepsize",self.step)
    self.rotateRegistrationX( self.step,10)
    self.rotateRegistrationX(-self.step,10)
    self.rotateRegistrationY( self.step,10)
    self.rotateRegistrationY( -self.step,10)
    self.rotateRegistrationZ( self.step,10)
    self.rotateRegistrationZ( -self.step,10)
    print(self.tick())   
    #self.colorWindow()  
  
  def step(self):
    alpha = int(cmp(self.tac-self.tick(),0)*self.tick()/float(self.WMAX)*50)
    print(alpha)
    return alpha

  def testingData(self):
    """Load some default data for development
    and set up a transform and viewing scenario for it.
    """
    if not slicer.util.getNodes('MRHead*'):
      import os
      fileName = "C:/Work/data/MR-head.nrrd"
      vl = slicer.modules.volumes.logic()
      volumeNode = vl.AddArchetypeScalarVolume (fileName, "MRHead", 0)
    if not slicer.util.getNodes('neutral*'):
      import os
      fileName = "C:/Work/data/neutral.nrrd"
      vl = slicer.modules.volumes.logic()
      volumeNode = vl.AddArchetypeScalarVolume (fileName, "neutral", 0)
    if not slicer.util.getNodes('movingToFixed'):
      # Create transform node
      transform = slicer.vtkMRMLLinearTransformNode()
      transform.SetName('movingToFixed')
      slicer.mrmlScene.AddNode(transform)
    head = slicer.util.getNode('MRHead')
    self.neutral = slicer.util.getNode('neutral')
    self.transformNode = slicer.util.getNode('movingToFixed')
    self.neutral.SetAndObserveTransformNodeID(self.transformNode.GetID())
    compositeNodes = slicer.util.getNodes('vtkMRMLSliceCompositeNode*')
    for compositeNode in compositeNodes.values():
      compositeNode.SetBackgroundVolumeID(head.GetID())
      compositeNode.SetForegroundVolumeID(self.neutral.GetID())
      compositeNode.SetForegroundOpacity(0.5)
    applicationLogic = slicer.app.applicationLogic()
    applicationLogic.FitSliceToAll()




    



