###########################################################################################
#
#	*** INTERACTIVE DATA VISUALIZATION (IDV) CONFIDENTIAL AND PROPRIETARY INFORMATION ***
#
#	This software is supplied under the terms of a license agreement or
#	nondisclosure agreement with Interactive Data Visualization, Inc. and
#   may not be copied, disclosed, or exploited except in accordance with
#   the terms of that agreement.
#
#      Copyright (c) 2003-2022 IDV, Inc.
#      All rights reserved in all media.
#
#      IDV, Inc.
#      http://www.idvinc.com


################################################################
# Imports

import maya.cmds as mc
import maya.mel as mel
import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx
import xml.dom.minidom as xmldom
import os.path as path
import sys


################################################################
# class SpeedTreeMaterial

class SpeedTreeMap:
	def __init__(self, red = 1.0, green = 1.0, blue = 1.0, file = ""):
		self.red = red
		self.green = green
		self.blue = blue
		self.file = file

class SpeedTreeMaterial:
	def __init__(self, name, twoSided = False, vertexOpacity = False, userData = ""):
		self.shader = None
		self.name = name
		self.twoSided = twoSided
		self.vertexOpacity = vertexOpacity
		self.userData = userData
		self.maps = { }


################################################################
# SpeedTreeImporterTranslatorBase

class SpeedTreeImporterTranslatorBase(OpenMayaMPx.MPxFileTranslator):
	def __init__(self):
		OpenMayaMPx.MPxFileTranslator.__init__(self)
	def haveWriteMethod(self):
		return False
	def haveReadMethod(self):
		return True
	def haveNamespaceSupport(self):
		return True
	def filter(self):
		return "*.stmat"
	def defaultExtension(self):
		return "stmat"
	def writer(self, fileObject, optionString, accessMode):
		pass

	def CreateFileTexture(self, filename, colorManagement = True):
		texFile = mc.shadingNode("file", asTexture = True, isColorManaged = colorManagement)
		if (filename.find("<UDIM>") > -1):
			mc.setAttr(texFile + ".uvTilingMode", 3)
			filename = filename.replace("<UDIM>", "1001")
		mc.setAttr(texFile + ".fileTextureName", filename, type = "string")
		tex2dPlacement = mc.shadingNode("place2dTexture", asUtility = True)
		mc.defaultNavigation(connectToExisting=True, source=tex2dPlacement, destination=texFile)
		'''mc.connectAttr(tex2dPlacement + ".outUV", texFile + ".uvCoord")
		mc.connectAttr(tex2dPlacement + ".outUvFilterSize", texFile + ".uvFilterSize")
		mc.connectAttr(tex2dPlacement + ".vertexCameraOne", texFile + ".vertexCameraOne")
		mc.connectAttr(tex2dPlacement + ".vertexUvThree", texFile + ".vertexUvThree")
		mc.connectAttr(tex2dPlacement + ".vertexUvTwo", texFile + ".vertexUvTwo")
		mc.connectAttr(tex2dPlacement + ".vertexUvOne", texFile + ".vertexUvOne")
		mc.connectAttr(tex2dPlacement + ".repeatV", texFile + ".repeatV")
		mc.connectAttr(tex2dPlacement + ".repeatU", texFile + ".repeatU")
		mc.connectAttr(tex2dPlacement + ".rotateFrame", texFile + ".rotateFrame")
		mc.connectAttr(tex2dPlacement + ".offsetV", texFile + ".offsetV")
		mc.connectAttr(tex2dPlacement + ".offsetU", texFile + ".offsetU")
		mc.setAttr(tex2dPlacement + ".ihi", 0)'''
		return texFile

	def ConnectMaterial(self, mat, sg):
		if (mc.attributeQuery("outColor", node = mat, exists = True)):
			mc.connectAttr(mat + ".outColor", sg + ".surfaceShader", force = True)
		else:
			mc.connectAttr(mat + '.message', sg + '.miMaterialShader', force = True)
			mc.connectAttr(mat + '.message', sg + '.miShadowShader', force = True)
			mc.connectAttr(mat + '.message', sg + '.miPhotonShader', force = True)

	def reader(self, fileObject, optionString, accessMode):
		try:
			doc = xmldom.parse(fileObject.expandedFullName())
			root = doc.getElementsByTagName('Materials');
			if len(root) > 0:
				# remember materials and shading groups that existed before import
				aBeforeMaterials = mc.ls(mat = True)
				aBeforeSets = mc.ls(sets = True)
				aBeforeObjects = mc.ls(tr = True)

				# load mesh
				meshFile = fileObject.expandedPath() + root[0].attributes["Mesh"].value
				extension = path.splitext(meshFile)[1]
				fileTypes = []
				OpenMaya.MFileIO.getFileTypes(fileTypes)
				blendInTexcoord = 1
				try:
					if (extension == ".abc" and "Alembic" not in fileTypes):
						print("SpeedTree ERROR: Alembic plugin is not loaded")
						raise
					if (extension == ".fbx" and "FBX" not in fileTypes):
						print("SpeedTree ERROR: FBX plugin is not loaded")
						raise
					if (extension == ".usd" and "USD Import" not in fileTypes):
						print("SpeedTree ERROR: USD plugin is not loaded")
						raise

					if (extension == ".abc"):
						mel.eval("AbcImport -mode import -fitTimeRange -rcs \"" + meshFile + "\"")
						blendInTexcoord = 0
					elif (extension == ".usd"):
						mel.eval("file -import -type \"USD Import\" -pr -ra true -importFrameRate true -options \"preferredMaterial=none;readAnimData=1;importInstances=1\" \"" + meshFile + "\"")
					else:
						# fix vertex normals when skinned
						mel.eval("FBXProperty \"Import|IncludeGrp|Geometry|OverrideNormalsLock\" -v 1")

						OpenMaya.MFileIO.importFile(meshFile)

				except:
					print("SpeedTree ERROR: Failed to load mesh file [" + meshFile + "]")
					#print(sys.exc_info())
					return None

				try:
					aAfterMaterials = mc.ls(mat = True)
					aAfterSets = mc.ls(sets = True)
					aAfterObjects = mc.ls(tr = True)

					# turn off vertex color display
					for newobj in aAfterObjects:
						if (newobj not in aBeforeObjects):
							mc.select(newobj)
							mc.polyOptions(colorShadedDisplay = False)
							#print (newobj)

					# load speedtree materials
					aNewMaterials = { }
					materials = root[0].getElementsByTagName('Material')
					for material in materials:
						stMaterial = SpeedTreeMaterial(material.attributes["Name"].value,
														material.attributes["TwoSided"].value == "1",
														material.attributes["VertexOpacity"].value == "1",
														material.attributes["UserData"].value)
						maps = material.getElementsByTagName('Map')
						for stmap in maps:
							newmap = SpeedTreeMap()
							try:
								newmap.file = stmap.attributes["File"].value
							except:
								try:
									newmap.red = newmap.green = newmap.blue = float(stmap.attributes["Value"].value)
								except:
									try:
										newmap.red = float(stmap.attributes["ColorR"].value)
										newmap.green = float(stmap.attributes["ColorG"].value)
										newmap.blue = float(stmap.attributes["ColorB"].value)
									except:
										pass

							stMaterial.maps[stmap.attributes["Name"].value] = newmap
						aNewMaterials[stMaterial.name] = stMaterial

					# hook new materials to the shading engines on the mesh
					for newset in aAfterSets:
						if (newset not in aBeforeSets):
							stMaterialName = None
							# first try shading group name (with or without SG at the end)
							if (newset in aNewMaterials):
								stMaterialName = newset
							elif (newset[:-2] in aNewMaterials):
								stMaterialName = newset[:-2]
							elif (newset[14:] in aNewMaterials):
								stMaterialName = newset[14:]
							else:
								# if not, try to find a similar material name
								shaderName = newset + ".surfaceShader"
								if (mc.objExists(shaderName)):
									matName = mc.connectionInfo(shaderName, sfd = True).split('.')[0]
									if (matName in aNewMaterials):
										stMaterialName = matName

							# make new material and hook it up
							if (stMaterialName != None):
								aShapes = mc.listConnections(newset + ".dagSetMembers")
								newmat = self.CreateMaterial(aNewMaterials[stMaterialName], aShapes, blendInTexcoord)
								aNewMaterials[stMaterialName].shader = newmat
								self.ConnectMaterial(newmat, newset)

					# delete all the new materials since we replaced them
					for mat in aAfterMaterials:
						if (mat not in 	aBeforeMaterials):
							aHistory = mc.listHistory(mat, pruneDagObjects = True)
							mc.delete(aHistory)

					# go back through and attempt to rename the materials
					for mat in iter(aNewMaterials.values()):
						if (mat.shader != None):
							mc.rename(mat.shader, mat.name)

					##############################################
					# Special Fix for shader assingments
					# List all Dag nodes
					all_objects = mc.ls(dag=True, long=True)

					# Create an empty list to store objects with mesh nodes
					mesh_objects = []

					# Iterate through all objects and check if they have mesh nodes
					for obj in all_objects:
						# Use 'listRelatives' to list children of the object
						children = mc.listRelatives(obj, children=True, fullPath=True) or []
						
						# Check if any of the children are of type 'mesh'
						for child in children:
							if mc.nodeType(child) == 'mesh':
								mesh_objects.append(obj)
								break  # If we find a mesh node, no need to check other children

					# Select the objects with mesh nodes
					mc.select(mesh_objects, replace=True)

					sel = mc.ls(selection=True)

					if (len(sel) == len(aNewMaterials)):
						# Iterate through each selected object
						for each in sel:
							matName = each + "_MatSG"
							
							# Select the current object
							mc.select(each)
							
							# Create and assign a shading group
							mc.sets(e=True, forceElement=matName)

				except:
					print("SpeedTree ERROR: Failed to update material connections")
					#print(sys.exc_info())

		except:
			print("SpeedTree ERROR: Failed to read SpeedTree stmat file")
			#print(sys.exc_info())


################################################################
# SpeedTreeImporterTranslator

class SpeedTreeImporterTranslator(SpeedTreeImporterTranslatorBase):
	description = "SpeedTree"
	def CreateMaterial(self, stMaterial, aShapes, blendInTexcoord):
		shader = mc.shadingNode("aiStandardSurface", asShader = True)
		#print ('Shader is done')
		#mc.setAttr(shader + ".base", 1.0)
		'''
		for shape in aShapes:
			if (mc.attributeQuery("ai_expcol", node=shape, exists=True) != False):
				mc.setAttr(shape + ".ai_expcol", 1)
		'''
		
		#mc.setAttr(shader + ".shader_mode", 1)
		#mc.setAttr(shader + ".ambientColor", 0.05, 0.05, 0.05)

		if ("Color" in stMaterial.maps):
			stmap = stMaterial.maps["Color"]
			if (stmap.file):
				textureNode = self.CreateFileTexture(stmap.file)
				mc.connectAttr(textureNode + ".outColor", shader + ".baseColor")
				mc.setAttr(textureNode + ".colorSpace", "sRGB", type="string")
				mc.setAttr(textureNode + ".ignoreColorSpaceFileRules", 1)
				#print ('Color Done')
			else:
				mc.setAttr(shader + ".baseColor", stmap.red, stmap.green, stmap.blue)

		if ("Normal" in stMaterial.maps):
			stmap = stMaterial.maps["Normal"]
			if (stmap.file):
				textureNode = self.CreateFileTexture(stmap.file)
				mc.setAttr(textureNode + ".colorSpace", "Raw", type="string")
				mc.setAttr(textureNode + ".ignoreColorSpaceFileRules", 1)
				normalNode = mc.shadingNode("aiNormalMap", asUtility = True)
				#mc.setAttr(normalNode + ".invertG", 1)
				mc.connectAttr(textureNode + ".outColor", normalNode + ".input")
				mc.connectAttr(normalNode + ".outValue", shader + ".normalCamera")
				#print ('normal done')
				for shape in aShapes:
					if (mc.attributeQuery("aiOpaque", node=shape+"_Shape", exists=True) != False):
						mc.setAttr(shape + "_Shape.aiSubdivType", 1)
						mc.setAttr(shape + "_Shape.aiSubdivIterations", 0)

		if ("Opacity" in stMaterial.maps):
			stmap = stMaterial.maps["Opacity"]
			if (stmap.file):
				textureNode = self.CreateFileTexture(stmap.file)
				mc.setAttr(textureNode + ".colorSpace", "Raw", type="string")
				mc.setAttr(textureNode + ".ignoreColorSpaceFileRules", 1)
				mc.connectAttr(textureNode + ".outColor", shader + ".opacity")
				
				for shape in aShapes:
					if (mc.attributeQuery("aiOpaque", node=shape+"_Shape", exists=True) != False):
						mc.setAttr(shape + "_Shape.aiOpaque", 0)
				
				
				#print ('opacity done')
		
		elif (stMaterial.vertexOpacity):
			userdata = mc.shadingNode("aiUserDataVec2", asUtility = True)
			mc.setAttr(userdata + ".vec2AttrName", "blend_ao", type="string")
			mc.connectAttr(userdata + ".outValueX", shader + ".opacityR")
			mc.connectAttr(userdata + ".outValueX", shader + ".opacityG")
			mc.connectAttr(userdata + ".outValueX", shader + ".opacityB")
			#print (aShapes)
			#print ('\n')
			for shape in aShapes:
				if (mc.attributeQuery("aiOpaque", node=shape+"_Shape", exists=True)):
					mc.setAttr(shape + "_Shape.aiOpaque", 0)
				#print (shape)
				
				if (mc.attributeQuery("aiExportColors", node=shape+"_Shape", exists=True)):
					mc.setAttr(shape + "_Shape.aiExportColors", 1)
				
				#print ('color export is done')

		if ("Gloss" in stMaterial.maps):
			stmap = stMaterial.maps["Gloss"]
			if (stmap.file):
				textureNode = self.CreateFileTexture(stmap.file)
				mc.setAttr(textureNode + ".colorSpace", "Raw", type="string")
				mc.setAttr(textureNode + ".ignoreColorSpaceFileRules", 1)
				mc.setAttr(textureNode + ".invert", True)
				mc.connectAttr(textureNode + ".outColorR", shader + ".specularRoughness")
				mc.connectAttr(textureNode + ".outColorR", shader + ".diffuseRoughness")
			else:
				mc.setAttr(shader + ".specularRoughness", 1.0 - stmap.red)
				mc.setAttr(shader + ".diffuseRoughness", 1.0 - stmap.red)

		if ("SubsurfaceAmount" in stMaterial.maps and "SubsurfaceColor" in stMaterial.maps):
			mc.setAttr(shader + ".thinWalled", True)
			if ("SubsurfaceAmount" in stMaterial.maps):
				stmap = stMaterial.maps["SubsurfaceAmount"]
				if (stmap.file):
					textureNode = self.CreateFileTexture(stmap.file)
					mc.setAttr(textureNode + ".colorSpace", "Raw", type="string")
					mc.setAttr(textureNode + ".ignoreColorSpaceFileRules", 1)
					mc.connectAttr(textureNode + '.outColorR', shader + '.subsurface')
				else:
					mc.setAttr(shader + '.subsurface', stmap.red)

			if ("SubsurfaceColor" in stMaterial.maps):
				stmap = stMaterial.maps["SubsurfaceColor"]
				if (stmap.file):
					textureNode = self.CreateFileTexture(stmap.file)
					mc.connectAttr(textureNode + '.outColor', shader + '.subsurfaceColor')
					mc.setAttr(textureNode + ".colorSpace", "sRGB", type="string")
				else:
					mc.setAttr(shader + '.subsurfaceColor', stmap.red, stmap.green, stmap.blue)

		return shader



################################################################
# SpeedTreeImporterArnoldTranslator
'''
class SpeedTreeImporterArnoldTranslator(SpeedTreeImporterTranslatorBase):
	description = "SpeedTree for Arnold"
	def haveReadMethod(self):
		return mc.pluginInfo("mtoa", q = True, l = True) # check to see if arnold plugin is available
	def CreateMaterial(self, stMaterial, aShapes, blendInTexcoord):
		isTwoSided = (stMaterial.twoSided and "Normal" in stMaterial.maps and not not stMaterial.maps["Normal"].file)
		shader = mc.shadingNode("aiStandardSurface", asShader = isTwoSided==0, asUtility = isTwoSided==1)
		for shape in aShapes:
			if (mc.attributeQuery("ai_expcol", node=shape, exists=True) != False):
				mc.setAttr(shape + ".ai_expcol", 1)

		mc.setAttr(shader + ".base", 1.0)
		if ("Color" in stMaterial.maps):
			stmap = stMaterial.maps["Color"]
			if (stmap.file):
				textureNode = self.CreateFileTexture(stmap.file)
				mc.connectAttr(textureNode + ".outColor", shader + ".baseColor")
				mc.setAttr(textureNode + ".colorSpace", "sRGB", type="string")
				mc.setAttr(textureNode + ".ignoreColorSpaceFileRules", 1)
			else:
				mc.setAttr(shader + ".baseColor", stmap.red, stmap.green, stmap.blue)

		if ("Opacity" in stMaterial.maps):
			stmap = stMaterial.maps["Opacity"]
			if (stmap.file):
				textureNode = self.CreateFileTexture(stmap.file)
				mc.setAttr(textureNode + ".colorSpace", "Raw", type="string")
				mc.connectAttr(textureNode + ".outColor", shader + ".opacity")
				for shape in aShapes:
					if (mc.attributeQuery("aiOpaque", node=shape, exists=True) != False):
						mc.setAttr(shape + ".aiOpaque", 0)
		elif (stMaterial.vertexOpacity):
			userdata = mc.shadingNode("aiUserDataVec2", asUtility = True)
			mc.setAttr(userdata + ".vec2AttrName", "blend_ao", type="string")
			mc.connectAttr(userdata + ".outValueX", shader + ".opacityR")
			mc.connectAttr(userdata + ".outValueX", shader + ".opacityG")
			mc.connectAttr(userdata + ".outValueX", shader + ".opacityB")
			for shape in aShapes:
				if (mc.attributeQuery("aiOpaque", node=shape, exists=True)):
					mc.setAttr(shape + ".aiOpaque", 0)
				if (mc.attributeQuery("aiExportColors", node=shape+"Shape", exists=True)):
					mc.setAttr(shape + "Shape.aiExportColors", 1)

		if ("Gloss" in stMaterial.maps):
			stmap = stMaterial.maps["Gloss"]
			if (stmap.file):
				textureNode = self.CreateFileTexture(stmap.file)
				mc.setAttr(textureNode + ".colorSpace", "Raw", type="string")
				mc.setAttr(textureNode + ".invert", True)
				mc.connectAttr(textureNode + ".outColorR", shader + ".specularRoughness")
				mc.connectAttr(textureNode + ".outColorR", shader + ".diffuseRoughness")
			else:
				mc.setAttr(shader + ".specularRoughness", 1.0 - stmap.red)
				mc.setAttr(shader + ".diffuseRoughness", 1.0 - stmap.red)

		if ("SubsurfaceAmount" in stMaterial.maps and "SubsurfaceColor" in stMaterial.maps):
			mc.setAttr(shader + ".thinWalled", True)
			if ("SubsurfaceAmount" in stMaterial.maps):
				stmap = stMaterial.maps["SubsurfaceAmount"]
				if (stmap.file):
					textureNode = self.CreateFileTexture(stmap.file)
					mc.setAttr(textureNode + ".colorSpace", "Raw", type="string")
					mc.connectAttr(textureNode + '.outColorR', shader + '.subsurface')
				else:
					mc.setAttr(shader + '.subsurface', stmap.red)

			if ("SubsurfaceColor" in stMaterial.maps):
				stmap = stMaterial.maps["SubsurfaceColor"]
				if (stmap.file):
					textureNode = self.CreateFileTexture(stmap.file)
					mc.connectAttr(textureNode + '.outColor', shader + '.subsurfaceColor')
					mc.setAttr(textureNode + ".colorSpace", "sRGB", type="string")
					mc.setAttr(textureNode + ".ignoreColorSpaceFileRules", 1)
				else:
					mc.setAttr(shader + '.subsurfaceColor', stmap.red, stmap.green, stmap.blue)

		if ("Normal" in stMaterial.maps):
			stmap = stMaterial.maps["Normal"]
			if (stmap.file):
				textureNode = self.CreateFileTexture(stmap.file)
				mc.setAttr(textureNode + ".colorSpace", "Raw", type="string")
				normalmap = mc.shadingNode("aiNormalMap", asUtility = True)
				mc.connectAttr(textureNode + ".outColor", normalmap + ".input")
				mc.connectAttr(normalmap + ".outValue", shader + ".normalCamera")
				for shape in aShapes:
					if (mc.attributeQuery("doubleSided", node=shape+"Shape", exists=True) != False):
						mc.setAttr(shape + "Shape.doubleSided", stMaterial.twoSided)
					if (mc.attributeQuery("aiExportTangents", node=shape+"Shape", exists=True) != False):
						mc.setAttr(shape + "Shape.aiExportTangents", 1)
				if (stMaterial.twoSided):
					frontshader = shader
					backshader = mc.duplicate(frontshader, ic=True)[0]
					shader = mc.shadingNode("aiTwoSided", asShader=True)
					mc.connectAttr(frontshader + ".outColor", shader + ".front")
					mc.connectAttr(backshader + ".outColor", shader + ".back")
					if (textureNode != None):
						backnormalmap = mc.shadingNode("aiNormalMap", asUtility = True)
						mc.setAttr(backnormalmap + ".invertX", True)
						mc.setAttr(backnormalmap + ".invertY", True)
						mc.connectAttr(textureNode + ".outColor", backnormalmap + ".input")
						mc.connectAttr(backnormalmap + ".outValue", backshader + ".normalCamera", force=True)

		return shader
'''

################################################################
# SpeedTreeImporterVRayTranslator

class SpeedTreeImporterVRayTranslator(SpeedTreeImporterTranslatorBase):
	description = "SpeedTree for V-Ray"
	def haveReadMethod(self):
		return mc.pluginInfo("vrayformaya", q = True, l = True) # check to see if vray plugin is available
	def CreateMaterial(self, stMaterial, aShapes, blendInTexcoord):
		shader = mc.shadingNode("VRayMtl", asShader = stMaterial.twoSided==0, asUtility = stMaterial.twoSided==1)

		mc.setAttr(shader + ".doubleSided", stMaterial.twoSided)
		twoSidedNode = None
		if (stMaterial.twoSided):
			twoSidedNode = mc.shadingNode("VRayMtl2Sided", asShader = True)
			mc.setAttr(twoSidedNode + ".translucencyTex", 0.0, 0.0, 0.0)
			mc.connectAttr(shader + ".outColor", twoSidedNode + ".frontMaterial")
			mc.connectAttr(shader + ".outColor", twoSidedNode + ".backMaterial")

		if ("Color" in stMaterial.maps):
			stmap = stMaterial.maps["Color"]
			if (stmap.file):
				textureNode = self.CreateFileTexture(stmap.file)
				mc.connectAttr(textureNode + ".outColor", shader + ".color")
			else:
				mc.setAttr(shader + ".color", stmap.red, stmap.green, stmap.blue)

		if ("Opacity" in stMaterial.maps):
			stmap = stMaterial.maps["Opacity"]
			if (stmap.file):
				mc.setAttr(shader + ".opacityMode", 1)
				textureNode = self.CreateFileTexture(stmap.file)
				mc.setAttr(textureNode + ".colorSpace", "Raw", type="string")
				mc.connectAttr(textureNode + ".outColor", shader + ".opacityMap")
		elif (stMaterial.vertexOpacity):
			# use vertex color for branch seam blending
			vertexColor = mc.shadingNode("VRayVertexColors", asTexture = True)
			mc.setAttr(vertexColor + ".type", 1)
			mc.setAttr(vertexColor + ".name", "blend_ao", type = "string")
			mc.setAttr(vertexColor + ".defaultColor", 1.0, 1.0, 1.0)
			mc.setAttr(vertexColor + ".useUVSets", blendInTexcoord)
			mc.connectAttr(vertexColor + ".outColor.outColorR", shader + ".opacityMap.opacityMapR")
			mc.connectAttr(vertexColor + ".outColor.outColorR", shader + ".opacityMap.opacityMapG")
			mc.connectAttr(vertexColor + ".outColor.outColorR", shader + ".opacityMap.opacityMapB")

		mc.setAttr(shader + ".brdfType", 3)
		mc.setAttr(shader + ".reflectionColor", 0.5, 0.5, 0.5)
		mc.setAttr(shader + ".useFresnel", 1)
		if ("Gloss" in stMaterial.maps):
			stmap = stMaterial.maps["Gloss"]
			if (stmap.file):
				textureNode = self.CreateFileTexture(stmap.file)
				mc.setAttr(textureNode + ".colorSpace", "Raw", type="string")
				mc.connectAttr(textureNode + ".outColorR", shader + ".reflectionGlossiness")
				mc.connectAttr(textureNode + ".outColorR", shader + ".refractionGlossiness")
				glossReverse = mc.shadingNode("reverse", asUtility = True)
				mc.connectAttr(textureNode + ".outColor", glossReverse + ".input")
				mc.connectAttr(glossReverse + ".outputX", shader + ".roughnessAmount")
			else:
				mc.setAttr(shader + ".reflectionGlossiness", stmap.red)
				mc.setAttr(shader + ".refractionGlossiness", stmap.red)
				mc.setAttr(shader + ".roughnessAmount", 1.0 - stmap.red)

		if ("Normal" in stMaterial.maps):
			stmap = stMaterial.maps["Normal"]
			if (stmap.file):
				normalTexture = self.CreateFileTexture(stmap.file)
				mc.setAttr(normalTexture + ".colorSpace", "Raw", type="string")
				if (twoSidedNode is None):
					mc.setAttr(shader + ".bumpMapType", 1)
					mc.setAttr(shader + ".bumpMult", 0.5)
					mc.connectAttr(normalTexture + ".outColor", shader + ".bumpMap")
				else:
					frontBump = mc.shadingNode("VRayBumpMtl", asUtility = True)
					mc.setAttr(frontBump + ".bumpMult", 0.5)
					mc.setAttr(frontBump + ".bumpMapType", 1)
					mc.connectAttr(shader + ".outColor", frontBump + ".base_material")
					mc.connectAttr(normalTexture + ".outColor", frontBump + ".bumpMap")
					backBump = mc.shadingNode("VRayBumpMtl", asUtility = True)
					mc.setAttr(backBump + ".bumpMult", -1.0)
					mc.setAttr(backBump + ".bumpMapType", 1)
					mc.connectAttr(shader + ".outColor", backBump + ".base_material")
					mc.connectAttr(normalTexture + ".outColor", backBump + ".bumpMap")
					mc.connectAttr(frontBump + ".outColor", twoSidedNode + ".frontMaterial", force = True)
					mc.connectAttr(backBump + ".outColor", twoSidedNode + ".backMaterial", force = True)

		if ((twoSidedNode is not None) and ("SubsurfaceColor" in stMaterial.maps or "SubsurfaceAmount" in stMaterial.maps)):
			mulNode = mc.shadingNode("multiplyDivide", asUtility = True)
			mc.connectAttr(mulNode + ".output", twoSidedNode + ".translucencyTex")

			if ("SubsurfaceAmount" in stMaterial.maps):
				stmap = stMaterial.maps["SubsurfaceAmount"]
				if (stmap.file):
					textureNode = self.CreateFileTexture(stmap.file)
					mc.setAttr(textureNode + ".colorSpace", "Raw", type="string")
					mc.connectAttr(textureNode + '.outColor', mulNode + '.input1')
				else:
					mc.setAttr(mulNode + '.input1', stmap.red, stmap.green, stmap.blue)

			if ("SubsurfaceColor" in stMaterial.maps):
				stmap = stMaterial.maps["SubsurfaceColor"]
				if (stmap.file):
					textureNode = self.CreateFileTexture(stmap.file)
					mc.connectAttr(textureNode + '.outColor', mulNode + '.input2')
				else:
					mc.setAttr(mulNode + '.input2', stmap.red, stmap.green, stmap.blue)

		if (twoSidedNode is not None):
			return twoSidedNode

		return shader


################################################################
# SpeedTreeImporterRendermanTranslator

class SpeedTreeImporterRendermanTranslator(SpeedTreeImporterTranslatorBase):
	description = "SpeedTree for Renderman"
	def haveReadMethod(self):
		return mc.pluginInfo("RenderMan_for_Maya", q = True, l = True) # check to see if renderman plugin is available
	def CreateMaterial(self, stMaterial, aShapes, blendInTexcoord):
		shader = mc.shadingNode("PxrSurface", asShader = True)

		mc.setAttr(shader + ".diffuseDoubleSided", stMaterial.twoSided)
		if ("Color" in stMaterial.maps):
			stmap = stMaterial.maps["Color"]
			if (stmap.file):
				textureNode = self.CreateFileTexture(stmap.file)
				mc.connectAttr(textureNode + ".outColor", shader + ".diffuseColor")
			else:
				mc.setAttr(shader + ".diffuseColor", stmap.red, stmap.green, stmap.blue)

		if ("Normal" in stMaterial.maps):
			stmap = stMaterial.maps["Normal"]
			if (stmap.file):
				textureNode = self.CreateFileTexture(stmap.file)
				mc.setAttr(textureNode + ".colorSpace", "Raw", type="string")
				normalNode = mc.shadingNode("PxrNormalMap", asUtility = True)
				mc.setAttr(normalNode + ".flipX", True)
				mc.setAttr(normalNode + ".flipY", True)
				mc.connectAttr(textureNode + ".outColor", normalNode + ".inputRGB")
				if (stMaterial.twoSided):
					backnormalNode = mc.shadingNode("PxrNormalMap", asUtility = True)
					mc.connectAttr(textureNode + ".outColor", backnormalNode + ".inputRGB")
					switchNode = mc.shadingNode("PxrSwitch", asUtility = True)
					shadedNode = mc.shadingNode("PxrShadedSide", asUtility = True)
					mc.connectAttr(shadedNode + ".resultF", switchNode + ".index")
					mc.connectAttr(backnormalNode + ".resultN", switchNode + ".inputsRGB[0]")
					mc.connectAttr(normalNode + ".resultN", switchNode + ".inputsRGB[1]")
					mc.connectAttr(switchNode + ".resultRGB", shader + ".bumpNormal")
				else:
					mc.connectAttr(normalNode + ".resultN", shader + ".bumpNormal")

		if ("Opacity" in stMaterial.maps):
			stmap = stMaterial.maps["Opacity"]
			if (stmap.file):
				textureNode = self.CreateFileTexture(stmap.file)
				mc.setAttr(textureNode + ".colorSpace", "Raw", type="string")
				mc.connectAttr(textureNode + ".outColorR", shader + ".presence")

		mc.setAttr(shader + ".specularDoubleSided", stMaterial.twoSided)
		mc.setAttr(shader + ".roughSpecularDoubleSided", stMaterial.twoSided)
		mc.setAttr(shader + ".specularEdgeColor", 1, 1, 1)
		mc.setAttr(shader + ".specularFresnelMode", 1)
		mc.setAttr(shader + ".specularModelType", 1)
		if ("Gloss" in stMaterial.maps):
			stmap = stMaterial.maps["Gloss"]
			if (stmap.file):
				textureNode = self.CreateFileTexture(stmap.file)
				mc.setAttr(textureNode + ".colorSpace", "Raw", type="string")
				roughness = mc.shadingNode("reverse", asUtility = True)
				mc.connectAttr(textureNode + ".outColor", roughness + ".input")
				mc.connectAttr(roughness + ".outputX", shader + ".diffuseRoughness")
				mc.connectAttr(roughness + ".outputX", shader + ".specularRoughness")
			else:
				mc.setAttr(shader + ".diffuseRoughness", 1.0 - stmap.red)
				mc.setAttr(shader + ".specularRoughness", 1.0 - stmap.red)

		if ("SubsurfaceAmount" in stMaterial.maps):
			stmap = stMaterial.maps["SubsurfaceAmount"]
			if (stmap.file):
				textureNode = self.CreateFileTexture(stmap.file)
				mc.setAttr(textureNode + ".colorSpace", "Raw", type="string")
				mc.connectAttr(textureNode + '.outColorR', shader + '.diffuseTransmitGain')
			else:
				mc.setAttr(shader + '.diffuseTransmitGain', stmap.red)
			stmap = stMaterial.maps["SubsurfaceColor"]
			if (stmap.file):
				textureNode = self.CreateFileTexture(stmap.file)
				mc.connectAttr(textureNode + '.outColor', shader + '.diffuseTransmitColor')
			else:
				mc.setAttr(shader + '.diffuseTransmitColor', stmap.red, stmap.green, stmap.blue)

		return shader


################################################################
# SpeedTreeImporterRedshiftTranslator

class SpeedTreeImporterRedshiftTranslator(SpeedTreeImporterTranslatorBase):
	description = "SpeedTree for Redshift"
	def haveReadMethod(self):
		return mc.pluginInfo("redshift4maya", q = True, l = True) # check to see if redshift plugin is available
	def CreateMaterial(self, stMaterial, aShapes, blendInTexcoord):
		shader = mc.shadingNode("RedshiftMaterial", asShader = True)

		if ("Color" in stMaterial.maps):
			stmap = stMaterial.maps["Color"]
			if (stmap.file):
				textureNode = self.CreateFileTexture(stmap.file)
				mc.connectAttr(textureNode + ".outColor", shader + ".diffuse_color")
			else:
				mc.setAttr(shader + ".diffuse_color", stmap.red, stmap.green, stmap.blue)

		if ("Normal" in stMaterial.maps):
			stmap = stMaterial.maps["Normal"]
			if (stmap.file):
				normalNode = mc.shadingNode("RedshiftNormalMap", asUtility = True)
				mc.setAttr(normalNode + ".tex0", stmap.file, type="string")
				if (stMaterial.twoSided):
					mulNode = mc.shadingNode("multiplyDivide", asUtility = True)
					mc.connectAttr(normalNode + ".outDisplacementVector", mulNode + ".input1")
					mc.setAttr(mulNode + ".input2", -1.0, -1.0, 1.0)
					switchNode = mc.shadingNode("RedshiftRaySwitch", asUtility = True)
					mc.setAttr(switchNode + ".cameraSwitchFrontBack", True)
					mc.connectAttr(normalNode + ".outDisplacementVector", switchNode + ".cameraColor")
					mc.connectAttr(mulNode + ".output", switchNode + ".cameraColorBack")
					mc.connectAttr(switchNode + ".outColor", shader + ".bump_input")
				else:
					mc.connectAttr(normalNode + ".outDisplacementVector", shader + ".bump_input")

		if ("Opacity" in stMaterial.maps):
			stmap = stMaterial.maps["Opacity"]
			if (stmap.file):
				textureNode = self.CreateFileTexture(stmap.file)
				mc.setAttr(textureNode + ".colorSpace", "Raw", type="string")
				mc.connectAttr(textureNode + ".outColor", shader + ".opacity_color")
		elif (stMaterial.vertexOpacity):
			# use vertex color for branch seam blending
			uvNode = mc.shadingNode("place2dTexture", asUtility = True)
			mc.setAttr(uvNode + ".rsUvSet", "blend_ao", type = "string")
			mc.connectAttr(uvNode + ".outU", shader + ".opacity_colorR")
			mc.connectAttr(uvNode + ".outU", shader + ".opacity_colorG")
			mc.connectAttr(uvNode + ".outU", shader + ".opacity_colorB")

		mc.setAttr(shader + ".refl_brdf", 1)
		if ("Gloss" in stMaterial.maps):
			stmap = stMaterial.maps["Gloss"]
			if (stmap.file):
				textureNode = self.CreateFileTexture(stmap.file)
				mc.setAttr(textureNode + ".colorSpace", "Raw", type="string")
				roughness = mc.shadingNode("reverse", asUtility = True)
				mc.connectAttr(textureNode + ".outColor", roughness + ".input")
				mc.connectAttr(roughness + ".outputX", shader + ".diffuse_roughness")
				mc.connectAttr(roughness + ".outputX", shader + ".refl_roughness")
				mc.connectAttr(roughness + ".outputX", shader + ".refr_roughness")
			else:
				mc.setAttr(shader + ".diffuse_roughness", 1.0 - stmap.red)
				mc.setAttr(shader + ".refl_roughness", 1.0 - stmap.red)
				mc.setAttr(shader + ".refr_roughness", 1.0 - stmap.red)

		if ("SubsurfaceAmount" in stMaterial.maps):
			stmap = stMaterial.maps["SubsurfaceAmount"]
			if (stmap.file):
				textureNode = self.CreateFileTexture(stmap.file)
				mc.setAttr(textureNode + ".colorSpace", "Raw", type="string")
				mc.connectAttr(textureNode + '.outColorR', shader + '.transl_weight')
			else:
				mc.setAttr(shader + '.transl_weight', stmap.red)
			stmap = stMaterial.maps["SubsurfaceColor"]
			if (stmap.file):
				textureNode = self.CreateFileTexture(stmap.file)
				mc.connectAttr(textureNode + '.outColor', shader + '.transl_color')
			else:
				mc.setAttr(shader + '.transl_color', stmap.red, stmap.green, stmap.blue)

		return shader


################################################################
# SpeedTreeImporterMentalRayTranslator

#class SpeedTreeImporterMentalRayTranslator(SpeedTreeImporterTranslatorBase):
#	description = "SpeedTree for Mental Ray"
#	def haveReadMethod(self):
#		return mc.pluginInfo("Mayatomr", q = True, l = True) # check to see if mental ray plugin is available
#	def CreateMaterial(self, stMaterial, aShapes, blendInTexcoord):
#		shader = mc.shadingNode("mia_material_x", asShader = True)
#
#		if ("Color" in stMaterial.maps):
#			stmap = stMaterial.maps["Color"]
#			if (stmap.file):
#				textureNode = self.CreateFileTexture(stmap.file)
#				mc.connectAttr(textureNode + ".outColor", shader + ".diffuse")
#			else:
#				mc.setAttr(shader + ".diffuse", stmap.red, stmap.green, stmap.blue)
#
#		mc.setAttr(shader + ".bump_mode", 3)
#		if ("Normal" in stMaterial.maps):
#			stmap = stMaterial.maps["Normal"]
#			if (stmap.file):
#				textureNode = self.CreateFileTexture(stmap.file)
#				mc.setAttr(textureNode + ".colorSpace", "Raw", type="string")
#				bump2dNode = mc.shadingNode("bump2d", asUtility = True)
#				mc.setAttr(bump2dNode + ".bumpInterp", 1)
#				mc.connectAttr(textureNode + ".outAlpha", bump2dNode + ".bumpValue")
#				misSetNormalNode = mc.shadingNode("misss_set_normal", asUtility = True)
#				mc.connectAttr(bump2dNode + ".outNormal", misSetNormalNode + ".normal")
#				mc.connectAttr(misSetNormalNode + ".outValue", shader + ".overall_bump")
#
#		if ("Opacity" in stMaterial.maps):
#			stmap = stMaterial.maps["Opacity"]
#			if (stmap.file):
#				textureNode = self.CreateFileTexture(stmap.file)
#				mc.setAttr(textureNode + ".colorSpace", "Raw", type="string")
#				# try to alleviate mental ray blurring the opacity map on glancing angles
#				mc.setAttr(textureNode + ".filterType", 0)
#				mc.connectAttr(textureNode + ".outColorR", shader + ".cutout_opacity")
#		elif (stMaterial.vertexOpacity):
#			# use vertex color for branch seam blending
#			if (blendInTexcoord):
#				uvChooser = mc.shadingNode('uvChooser', n='blend_ao', asUtility = True)
#				mc.connectAttr(uvChooser + ".outUv.outU", shader + ".cutout_opacity")
#				index = 0
#				for shape in aShapes:
#					mc.connectAttr(shape + ".uvSet[1].uvSetName", uvChooser + ".uvSets[" + str(index) + "]")
#					index += 1
#			else:
#				vertexColor = mc.shadingNode("mentalrayVertexColors", asUtility = True)
#				mc.setAttr(vertexColor + ".defaultColor", 1.0, 1.0, 1.0)
#				mc.connectAttr(vertexColor + ".outColorR", shader + ".cutout_opacity")
#				index = 0
#				for shape in aShapes:
#					mc.connectAttr(shape + ".colorSet[0].colorName", vertexColor + ".cpvSets[" + str(index) + "]")
#					index += 1
#
#		mc.setAttr(shader + ".brdf_fresnel", 1)
#		mc.setAttr(shader + ".refl_color", 1.0, 1.0, 1.0)
#		mc.setAttr(shader + ".reflectivity", 0.25)
#		if ("Gloss" in stMaterial.maps):
#			stmap = stMaterial.maps["Gloss"]
#			if (stmap.file):
#				textureNode = self.CreateFileTexture(stmap.file)
#				mc.setAttr(textureNode + ".colorSpace", "Raw", type="string")
#				mc.connectAttr(textureNode + ".outColorR", shader + ".refl_gloss")
#				mc.connectAttr(textureNode + ".outColorR", shader + ".refr_gloss")
#				glossReverse = mc.shadingNode("reverse", asUtility = True)
#				mc.connectAttr(textureNode + ".outColor", glossReverse + ".input")
#				mc.connectAttr(glossReverse + ".outputX", shader + ".diffuse_roughness")
#			else:
#				mc.setAttr(shader + ".diffuse_roughness", 1.0 - stmap.red)
#				mc.setAttr(shader + ".refl_gloss", stmap.red)
#				mc.setAttr(shader + ".refr_gloss", stmap.red)
#
#		if ("SubsurfaceAmount" in stMaterial.maps):
#			stmap = stMaterial.maps["SubsurfaceAmount"]
#			mc.setAttr(shader + '.thin_walled', 1)
#			mc.setAttr(shader + '.refr_translucency', 1)
#			mc.setAttr(shader + '.refr_trans_weight', 1.0)
#			if (stmap.file):
#				textureNode = self.CreateFileTexture(stmap.file)
#				mc.setAttr(textureNode + ".colorSpace", "Raw", type="string")
#				mc.connectAttr(textureNode + '.outColorR', shader + '.transparency')
#			else:
#				mc.setAttr(shader + '.transparency', stmap.red)
#
#			stmap = stMaterial.maps["SubsurfaceColor"]
#			if (stmap.file):
#				textureNode = self.CreateFileTexture(stmap.file)
#				mc.connectAttr(textureNode + '.outColor', shader + '.refr_color')
#				mc.connectAttr(textureNode + '.outColor', shader + '.refr_trans_color')
#			else:
#				mc.setAttr(shader + '.refr_color', stmap.red, stmap.green, stmap.blue)
#				mc.setAttr(shader + '.refr_trans_color', stmap.red, stmap.green, stmap.blue)
#
#		return shader


################################################################
# initializePlugin

def initializePlugin(mObject):
	mPlugin = OpenMayaMPx.MFnPlugin(mObject, "SpeedTree", "9.0", "Any")
	for subclass in SpeedTreeImporterTranslatorBase.__subclasses__():
		mPlugin.registerFileTranslator(subclass.description, None, lambda:OpenMayaMPx.asMPxPtr(subclass( )), None, None, True)


################################################################
# uninitializePlugin

def uninitializePlugin(mObject):
	mPlugin = OpenMayaMPx.MFnPlugin(mObject)
	for subclass in SpeedTreeImporterTranslatorBase.__subclasses__():
		mPlugin.deregisterFileTranslator(subclass.description)

