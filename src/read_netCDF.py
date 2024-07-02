# imports
import sys
import os
sys.path.append(os.getenv('ISSM_DIR') + '/bin')
sys.path.append(os.getenv('ISSM_DIR') + '/lib')
from issmversion import issmversion

# from netCDF4 import Dataset
from h5netcdf.legacyapi import Dataset
import numpy as np
import numpy.ma as ma
from os import path, remove
from model import *
import re
from results import *
from m1qn3inversion import m1qn3inversion
from taoinversion import taoinversion
from collections import OrderedDict
import sys
from massfluxatgate import massfluxatgate



'''
Given a NetCDF4 file, this set of functions will perform the following:
    1. Enter each group of the file.
    2. For each variable in each group, update an empty model with the variable's data
    3. Enter nested groups and repeat
'''


# make a model framework to fill that is in the scope of this file
model_copy = model()

def read_netCDF(filename, verbose = False):
    if verbose:
        print('NetCDF42C v1.2.0')

    '''
    filename = path and name to save file under
    verbose = T/F = show or muted log statements. Naturally muted
    '''

    # this is a precaution so that data is not lost
    try:
        # check if path exists
        if path.exists(filename):
            if verbose:
                print('Opening {} for reading'.format(filename))
            else: pass
    
            # open the given netCDF4 file
            NCData = Dataset(filename, 'r')
            print(NCData)
            # remove masks from numpy arrays for easy conversion
            # NCData.set_auto_mask(False)
        else:
            return 'The file you entered does not exist or cannot be found in the current directory'
        
        # in order to handle some subclasses in the results class, we have to utilize this band-aid
        # there will likely be more band-aids added unless a class name library is created with all class names that might be added to a md
        try:
            # if results has meaningful data, save the name of the subclass and class instance
            NCData.groups['results']
            make_results_subclasses(NCData, verbose)
        except:
            pass
    
        # similarly, we need to check and see if we have an m1qn3inversion class instance
        try:
            NCData.groups['inversion']
            check_inversion_class(NCData, verbose)
        except:
            pass
        
        # walk through each group looking for subgroups and variables
        for group in NCData.groups.keys():
            if 'debris' in group:
                pass
            else:
                # have to send a custom name to this function: filename.groups['group']
                name = "NCData.groups['" + str(group) + "']"
                print('name:', name)
                walk_nested_groups(name, NCData, verbose)
        
        if verbose:
            print("Model Successfully Loaded.")
            
        NCData.close()
        
        return model_copy

    # just in case something unexpected happens
    except Exception as e:
        if 'NCData' in locals():
            NCData.close()
        raise e

def make_results_subclasses(NCData, verbose = False):
    '''
        There are 3 possible subclasses: solution, solutionstep, resultsdakota.
        In the NetCDF file these are saved as a list of strings. Ie, say there are 2
        instances of solution under results, StressbalanceSolution and TransientSolution. 
        In the NetCDF file we would see solution = "StressbalanceSolution", "TransientSolution"
        To deconstruct this, we need to iteratively assign md.results.StressbalanceSolution = solution()
        and md.results.TransientSolution = solution() and whatever else.
    '''
    # start with the subclasses
    for subclass in NCData.groups['results'].variables.keys():
        class_instance = subclass + '()'

        # now handle the instances
        for instance in NCData.groups['results'].variables[subclass][:]:
            # this is an ndarray of numpy bytes_ that we have to convert to strings
            class_instance_name = instance.tobytes().decode('utf-8').strip()
            # from here we can make new subclasses named as they were in the model saved
            setattr(model_copy.results, class_instance_name, eval(class_instance))
            if verbose:
                print(f'Successfully created results subclass instance {class_instance} named {class_instance_name}.')


def check_inversion_class(NCData, verbose = False):
    # get the name of the inversion class: either inversion or m1qn3inversion or taoinversion
    inversion_class_is = NCData.groups['inversion'].variables['inversion_class_name'][:][...].tobytes().decode()
    if inversion_class_is == 'm1qn3inversion':
        # if it is m1qn3inversion we need to instantiate that class since it's not native to model()
        model_copy.inversion = m1qn3inversion(model_copy.inversion)
        if verbose:
            print('Conversion successful')
    elif inversion_class_is == 'taoinversion':
        # if it is taoinversion we need to instantiate that class since it's not native to model()
        model_copy.inversion = taoinverion()
        if verbose:
            print('Conversion successful')
    else: pass


def walk_nested_groups(group_location_in_file, NCData, verbose = False):
    # first, we enter the group by: filename.groups['group_name']
    # second we search the current level for variables: filename.groups['group_name'].variables.keys()
    # at this step we check for multidimensional structure arrays/ arrays of objects and filter them out
    # third we get nested group keys by: filename.groups['group_name'].groups.keys()
    # if a nested groups exist, repeat all
    print('Doing nested groups')
    print('For location:', group_location_in_file)
    print('Looking in:', group_location_in_file + '.variables.keys()')
    print(list(eval(group_location_in_file + '.variables.keys()')))
    for variable in eval(group_location_in_file + '.variables.keys()'):
        if 'is_object' not in locals():
            if variable == 'this_is_a_nested' and 'results' in group_location_in_file and 'qmu' not in group_location_in_file:
                # have to do some string deconstruction to get the name of the class instance/last group from 'NetCDF.groups['group1'].groups['group1.1']'
                pattern = r"\['(.*?)'\]"
                matches = re.findall(pattern, group_location_in_file)
                name_of_struct = matches[-1] #eval(group_location_in_file + ".variables['solution']") 
                deserialize_nested_results_struct(group_location_in_file, name_of_struct, NCData)
                is_object = True
    
            elif variable == 'name_of_cell_array':
                # reconstruct an array of elements
                deserialize_array_of_objects(group_location_in_file, model_copy, NCData, verbose)
                is_object = True
    
            elif variable == 'this_is_a_nested' and 'qmu' in group_location_in_file:
                if verbose:
                    print('encountered qmu structure that is not yet supported.')
                else: pass
                    
                is_object = True
        
            else:
                location_of_variable_in_file = group_location_in_file + ".variables['" + str(variable) + "']"
                print('location of variable in file:', location_of_variable_in_file)
                # group_location_in_file is like filename.groups['group1'].groups['group1.1'].groups['group1.1.1']
                # Define the regex pattern to match the groups within brackets
                pattern = r"\['(.*?)'\]"
                # Use regex to find all matches and return something like 'group1.group1.1.group1.1.1 ...' where the last value is the name of the variable
                matches = re.findall(pattern, location_of_variable_in_file)
                variable_name = matches[-1]
                location_of_variable_in_model = '.'.join(matches[:-1])
                print(location_of_variable_in_file)
                print(location_of_variable_in_model)
                print(variable_name)
                deserialize_data(location_of_variable_in_file, location_of_variable_in_model, variable_name, NCData, verbose=verbose)

    # if one of the variables above was an object, further subclasses will be taken care of when reconstructing it
    if 'is_object' in locals():
        pass
    else:
        for nested_group in eval(group_location_in_file + '.groups.keys()'):
            new_nested_group = group_location_in_file + "['" + str(nested_group) + "']"
            walk_nested_groups(new_nested_group, NCData, verbose=verbose)



'''
    MATLAB has Multidimensional Structure Arrays in 2 known classes: results and qmu.
    The python classes results.py and qmu.py emulate this MATLAB object in their own
    unique ways. The functions in this script will assign data to either of these 
    classes such that the final structure is compatible with its parent class.
'''

def deserialize_nested_results_struct(group_location_in_file, name_of_struct, NCData, verbose = False):
    '''
    A common multidimensional array is the 1xn md.results.TransientSolution object.

    The way that this object emulates the MATLAB mutli-dim. struct. array is with 
    the solution().steps attr. which is a list of solutionstep() instances
        The process to recreate is as follows:
            1. Get instance of solution() with solution variable (the instance is made in make_results_subclasses)
            2. For each subgroup, create a solutionstep() class instance
             2a. Populate the instance with the key:value pairs
             2b. Append the instance to the solution().steps list
    '''
    # step 1
    class_instance_name = name_of_struct
    
    # for some reason steps is not already a list
    setattr(model_copy.results.__dict__[class_instance_name], 'steps', list())

    steps = model_copy.results.__dict__[class_instance_name].steps
    
    # step 2
    layer = 1
    for subgroup in eval(group_location_in_file + ".groups.keys()"):
        solutionstep_instance = solutionstep()
        # step 2a
        subgroup_location_in_file = group_location_in_file + ".groups['" + subgroup + "']"
        for key in eval(subgroup_location_in_file + ".variables.keys()"):
            value = eval(subgroup_location_in_file + ".variables['" + str(key) + "'][:]")
            setattr(solutionstep_instance, key, value)
        # step 2b
        steps.append(solutionstep_instance)
        if verbose:
            print('Succesfully loaded layer ' + str(layer) + ' to results.' + str(class_instance_name) + ' struct.')
        else: pass
        layer += 1

    if verbose:
        print('Successfully recreated results structure ' + str(class_instance_name))



def deserialize_array_of_objects(group_location_in_file, model_copy, NCData, verbose):
    '''
        The structure in netcdf for groups with the name_of_cell_array variable is like:

        group: 2x6_cell_array_of_objects {
            name_of_cell_array = <name_of_cell_array>

            group: Row_1_of_2 {
                group: Col_1_of_6 {
                    ... other groups can be here that refer to objects
                } // group Col_6_of_6
            } // group Row_1_of_2

            group: Row_2_of_2 {
                group: Col_1_of_6 {
                    ... other groups can be here that refer to objects
                } // group Col_6_of_6
            } // group Row_2_of_2
        } // group 2x6_cell_array_of_objects

        We have to navigate this structure to extract all the data and recreate the 
        original structure when the model was saved
    '''

    if verbose: 
        print(f"Loading array of objects.")

    # get the name_of_cell_array, rows and cols vars
    name_of_cell_array_varID = eval(group_location_in_file + ".variables['name_of_cell_array']")
    rows_varID = eval(group_location_in_file + ".variables['rows']")
    cols_varID = eval(group_location_in_file + ".variables['cols']")

    name_of_cell_array = name_of_cell_array_varID[:][...].tobytes().decode()
    rows = rows_varID[:]
    cols = cols_varID[:]

    # now we work backwards: make the array, fill it in, and assign it to the model

    # make the array
    array = list()

    subgroups = eval(group_location_in_file + ".groups") #.keys()")

    # enter each subgroup, get the data, assign it to the corresponding index of cell array
    if rows > 1:
        # we go over rows
        # set index for rows
        row_idx = 0
        for row in list(subgroups):
            # make list for each row
            current_row = list()
            columns = subgroups[str(row)].groups.keys()

            # set index for columns
            col_idx = 0

            # iterate over columns
            for col in list(columns):
                # now get the variables 
                current_col_vars = columns.groups[str(col)].variables

                # check for special datastructures                
                if "class_is_a" in current_col_vars:
                    class_name = subgroups[str(col)].variables['class_is_a'][:][...].tobytes().decode()
                    col_data = deserialize_class_instance(class_name, columns.groups[str(col)], NCData, verbose)
                    is_object = True
                elif "this_is_a_nested" in current_col_vars:
                    # functionality not yet supported
                    print('Error: Cell Arrays of structs not yet supported!')
                    is_object = True
                else:
                    if 'is_object_' in locals():
                        pass
                        # already taken care of
                    else:
                        # store the variables as normal -- to be added later
                        print('Error: Arrays of mixed objects not yet supported!')
                        for var in current_col_vars:
                            # this is where that functionality would be handled
                            pass
                col_idx += 1
                # add the entry to our row list
                current_row.append(col_data)

            # add the list of columns to the array
            array.append(current_row)
            row_idx += 1

    else:
        # set index for columns
        col_idx = 0

        # iterate over columns
        for col in list(subgroups):
            # now get the variables 
            current_col_vars = subgroups[str(col)].variables
            
            # check for special datastructures
            if "class_is_a" in current_col_vars:
                class_name = subgroups[str(col)].variables['class_is_a'][:][...].tobytes().decode()
                col_data = deserialize_class_instance(class_name, subgroups[str(col)], NCData, verbose)
                is_object = True
            elif "this_is_a_nested" in current_col_vars:
                # functionality not yet supported
                print('Error: Cell Arrays of structs not yet supported!')
                is_object = True
            else:
                if 'is_object_' in locals():
                    pass
                    # already taken care of
                else:
                    # store the variables as normal -- to be added later
                    print('Error: Arrays of mixed objects not yet supported!')
                    for var in current_col_vars:
                        # this is where that functionality would be handled
                        pass
            col_idx += 1
            # add the list of columns to the array
            array.append(col_data)

    # finally, add the attribute to the model
    pattern = r"\['(.*?)'\]"
    matches = re.findall(pattern, group_location_in_file)
    variable_name = matches[0]
    setattr(model_copy.__dict__[variable_name], name_of_cell_array, array)

    if verbose:
        print(f"Successfully loaded array of objects: {name_of_cell_array} to {variable_name}")



def deserialize_class_instance(class_name, group, NCData, verbose=False):

    if verbose:
        print(f"Loading class: {class_name}")

    # this function requires the class module to be imported into the namespace of this file.
    # we make a custom error in case the class module is not in the list of imported classes.
    # most ISSM classes are imported by from <name> import <name>
    class ModuleError(Exception):
        pass
    
    if class_name not in sys.modules:
        raise ModuleError(str('Model requires the following class to be imported from a module: ' + class_name + ". Please add the import to read_netCDF.py in order to continue."))

    # Instantiate the class
    class_instance = eval(class_name + "()")

    # Get and assign properties
    subgroups = list(group.groups.keys())

    if len(subgroups) == 1:
        # Get properties
        subgroup = group[subgroups[0]]
        varIDs = subgroup.variables.keys()
        for varname in varIDs:
            # Variable metadata
            var = subgroup[varname]

            # Data
            if 'char' in var.dimensions[0]:
                data = var[:][...].tobytes().decode()
            else:
                data = var[:]

            # Some classes may have permissions, so we skip those
            try:
                setattr(class_instance, varname, data)
            except:
                pass
    else:
        # Not supported
        pass

    if verbose: 
        print(f"Successfully loaded class instance {class_name} to model")
    return class_instance



def deserialize_data(location_of_variable_in_file, location_of_variable_in_model, variable_name, NCData, verbose = False):
    # as simple as navigating to the location_of_variable_in_model and setting it equal to the location_of_variable_in_file
    # NetCDF4 has a property called "_FillValue" that sometimes saves empty lists, so we have to catch those
    FillValue = -9223372036854775806
    print(location_of_variable_in_file)
    print(eval(location_of_variable_in_file))
    print(eval(location_of_variable_in_file + '.__dir__()'))
    try:
        # results band-aid...
        if str(location_of_variable_in_model + '.' + variable_name) in ['results.solutionstep', 'results.solution', 'results.resultsdakota']:
            pass
        # qmu band-aid
        elif 'qmu.statistics.method' in str(location_of_variable_in_model + '.' + variable_name):
            pass
        # handle any strings:
        elif 'char' in eval(location_of_variable_in_file + '.dimensions[0]'):
            setattr(eval('model_copy.' + location_of_variable_in_model), variable_name, eval(location_of_variable_in_file + '[:][...].tobytes().decode()'))
        # handle ndarrays + lists
        elif len(eval(location_of_variable_in_file + '[:]'))>1:
            # check for bool
            try: # there is only one datatype assigned the attribute 'units' and that is bool, so anything else will go right to except
                if eval(location_of_variable_in_file + '.units') == 'bool':
                    setattr(eval('model_copy.' + location_of_variable_in_model), variable_name, np.array(eval(location_of_variable_in_file + '[:]'), dtype = bool))
                else:
                    setattr(eval('model_copy.' + location_of_variable_in_model), variable_name, eval(location_of_variable_in_file + '[:]'))
            except:
                setattr(eval('model_copy.' + location_of_variable_in_model), variable_name, eval(location_of_variable_in_file + '[:]'))
        # catch everything else
        else:
            # check for FillValue. use try/except because try block will only work on datatypes like int64, float, single element lists/arrays ect and not nd-arrays/n-lists etc
            try:
                # this try block will only work on single ints/floats/doubles and will skip to the except block for all other cases
                var_to_save = eval(location_of_variable_in_file + '[:][0]')  # note the [0] on the end
                if FillValue == var_to_save:
                    setattr(eval('model_copy.' + location_of_variable_in_model), variable_name, [])
                else:
                    if var_to_save.is_integer():
                        setattr(eval('model_copy.' + location_of_variable_in_model), variable_name, int(var_to_save))
                    else:
                        # we have to convert numpy datatypes to native python types with .item()
                        setattr(eval('model_copy.' + location_of_variable_in_model), variable_name, var_to_save.item())
            except:
                setattr(eval('model_copy.' + location_of_variable_in_model), variable_name, eval(location_of_variable_in_file + '[:]'))
    except AttributeError:
        deserialize_dict(location_of_variable_in_file, location_of_variable_in_model, NCData, verbose=verbose)

    if verbose:
        print('Successfully loaded ' + location_of_variable_in_model + '.' + variable_name + ' into model.')



def deserialize_dict(location_of_variable_in_file, location_of_variable_in_model, NCData, verbose = False):
    FillValue = -9223372036854775806

    # the key will be the last item in the location
    key = ''.join(location_of_variable_in_model.split('.')[-1])

    # update the location to point to the dict instead of the dict key
    location_of_variable_in_model = '.'.join(location_of_variable_in_model.split('.')[:-1])

    # verify we're working with a dict:
    if isinstance(eval('model_copy.' + location_of_variable_in_model), OrderedDict):
        dict_object = eval('model_copy.' + location_of_variable_in_model)
        
        # handle any strings:
        if 'char' in eval(location_of_variable_in_file + '.dimensions[0]'):
            data = eval(location_of_variable_in_file + '[:][...].tobytes().decode()')
            dict_object.update({key: data})
            
        # handle ndarrays + lists
        elif len(eval(location_of_variable_in_file + '[:]'))>1:
            # check for bool
            try: # there is only one datatype assigned the attribute 'units' and that is bool, so anything else will go right to except
                if eval(location_of_variable_in_file + '.units') == 'bool':
                    data = np.array(eval(location_of_variable_in_file + '[:]'), dtype = bool)
                    dict_object.update({key: data})
                else:
                    data = eval(location_of_variable_in_file + '[:]')
                    dict_object.update({key: data})
            except:
                data = eval(location_of_variable_in_file + '[:]')
                dict_object.update({key: data})
        # catch everything else
        else:
            # check for FillValue. use try/except because try block will only work on datatypes like int64, float, single element lists/arrays ect and not nd-arrays/n-lists etc
            try:
                # this try block will only work on single ints/floats/doubles and will skip to the except block for all other cases
                if FillValue == eval(location_of_variable_in_file + '[:][0]'):
                    dict_object.update({key: []})
                else:
                    # we have to convert numpy datatypes to native python types with .item()
                    var_to_save = eval(location_of_variable_in_file + '[:][0]')  # note the [0] on the end
                    dict_object.update({key:  var_to_save.item()})
            except:
                data = eval(location_of_variable_in_file + '[:]')
                dict_object.update({key: data})
    else:
        print(f"Unrecognized object was saved to NetCDF file and cannot be reconstructed: {location_of_variable_in_model}")
