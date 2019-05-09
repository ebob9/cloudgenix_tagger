#!/usr/bin/env python
import sys
import os
import argparse

####
#
# Enter other desired optional system modules here.
#
####

import json
import re
from copy import deepcopy
import csv

####
#
# End other desired system modules.
#
####

# Import CloudGenix Python SDK
try:
    import cloudgenix
    jdout = cloudgenix.jdout
    jdout_detailed = cloudgenix.jdout_detailed
    jd = cloudgenix.jd
except ImportError as e:
    cloudgenix = None
    sys.stderr.write("ERROR: 'cloudgenix' python module required. (try 'pip install cloudgenix').\n {0}\n".format(e))
    sys.exit(1)


# Import Progressbar2
try:
    from progressbar import Bar, ETA, Percentage, ProgressBar
except ImportError as e:
    Bar = None
    ETA = None
    Percentage = None
    ProgressBar = None
    sys.stderr.write("ERROR: 'progressbar2' python module required. (try 'pip install progressbar2').\n {0}\n".format(e))
    sys.exit(1)

# Import tabulate
try:
    from tabulate import tabulate
except ImportError as e:
    tabulate = None
    sys.stderr.write("ERROR: 'tabulate' python module required. (try 'pip install tabulate').\n {0}\n".format(e))
    sys.exit(1)


# Check for cloudgenix_settings.py config file in cwd.
sys.path.append(os.getcwd())
try:
    from cloudgenix_settings import CLOUDGENIX_AUTH_TOKEN

except ImportError:
    # if cloudgenix_settings.py file does not exist,
    # Get AUTH_TOKEN/X_AUTH_TOKEN from env variable, if it exists. X_AUTH_TOKEN takes priority.
    if "X_AUTH_TOKEN" in os.environ:
        CLOUDGENIX_AUTH_TOKEN = os.environ.get('X_AUTH_TOKEN')
    elif "AUTH_TOKEN" in os.environ:
        CLOUDGENIX_AUTH_TOKEN = os.environ.get('AUTH_TOKEN')
    else:
        # not set
        CLOUDGENIX_AUTH_TOKEN = None

try:
    # Also, seperately try and import USERNAME/PASSWORD from the config file.
    from cloudgenix_settings import CLOUDGENIX_USER, CLOUDGENIX_PASSWORD

except ImportError:
    # will get caught below
    CLOUDGENIX_USER = None
    CLOUDGENIX_PASSWORD = None


# Handle differences between python 2 and 3. Code can use text_type and binary_type instead of str/bytes/unicode etc.
if sys.version_info < (3,):
    text_type = unicode
    binary_type = str
else:
    text_type = str
    binary_type = bytes


####
#
# Start custom modifiable code
#
####

SUPPORTED_OBJECTS = ['sites', 'elements', 'interfaces', 'circuitcatagories']

GLOBAL_MY_SCRIPT_NAME = "CloudGenix Tagger"
GLOBAL_MY_SCRIPT_VERSION = "v1.0.0"

ELEMENT_PUT_ITEMS= [
    "cluster_member_id",
    "cluster_insertion_mode",
    "description",
    "site_id",
    "_schema",
    "_etag",
    "sw_obj",
    "id",
    "name",
    "l3_direct_private_wan_forwarding",
    "l3_lan_forwarding",
    "network_policysetstack_id",
    "priority_policysetstack_id",
    "spoke_ha_config",
    "tags"
]


class CloudGenixTaggerError(Exception):
    """
    Custom exception for errors, allows errors to be caught if using as function instead of script.
    """
    pass


def throw_error(message, resp=None, cr=True):
    """
    Non-recoverable error, write message to STDERR and exit or raise exception
    :param message: Message text
    :param resp: Optional - CloudGenix SDK Response object
    :param cr: Optional - Use (or not) Carriage Returns.
    :return: No Return, throws exception.
    """
    output = "ERROR: " + str(message)
    if cr:
        output += "\n"
    sys.stderr.write(output)
    if resp is not None:
        output2 = str(jdout_detailed(resp))
        if cr:
            output2 += "\n"
        sys.stderr.write(output2)
    raise CloudGenixTaggerError(message)


def throw_warning(message, resp=None, cr=True):
    """
    Recoverable Warning.
    :param message: Message text
    :param resp: Optional - CloudGenix SDK Response object
    :param cr: Optional - Use (or not) Carriage Returns.
    :return: None
    """
    output = "WARNING: " + str(message)
    if cr:
        output += "\n"
    sys.stderr.write(output)
    if resp is not None:
        output2 = str(jdout_detailed(resp))
        if cr:
            output2 += "\n"
        sys.stderr.write(output2)
    return


def extract_tags(cgx_dict):
    """
    This function looks at a CloudGenix config object, and gets tags.
    :param cgx_dict: CloudGenix config dict, expects "tags" keys supported in root.
    :return: list of tags present.
    """

    # tags exist, return them.
    tags = cgx_dict.get("tags", [])
    if tags is None:
        tags = []

    # return unique tags.
    return list(set(tags))


def put_tags(new_tag_list, cgx_dict):
    """
    This function looks at a CloudGenix config object, and puts tags.
    :param new_tag_list: List of tags to add if not already present.
    :param cgx_dict: CloudGenix config dict, expects "tags" keys supported in root.
    :return: CloudGenix config dict with added tags
    """

    new_cgx_dict = deepcopy(cgx_dict)

    tags = new_cgx_dict.get("tags", [])
    if tags is None:
        tags = []
    # add new tags to tags
    tags.extend([tag for tag in new_tag_list if tag not in tags])
    # update dict
    new_cgx_dict["tags"] = tags

    return new_cgx_dict


def remove_tags(remove_tag_list, cgx_dict):
    """
    This function looks at a CloudGenix config object, looks in tags, removes all matching tags.
    :param remove_tag_list: List of tags to remove.
    :param cgx_dict: CloudGenix config dict, expects "description" keys supported in root.
    :return: list of tags present.
    """

    new_cgx_dict = deepcopy(cgx_dict)

    tags = new_cgx_dict.get("tags", [])
    if tags is None:
        tags = []
    # add new tags to tags
    tags = [tag for tag in tags if tag not in remove_tag_list]
    # update dict, ensure no duplicate tags.
    new_cgx_dict["tags"] = list(set(tags))

    return new_cgx_dict


def extract_items(resp_object, error_label=None):
    """
    Extract
    :param resp_object: CloudGenix Extended Requests.Response object.
    :param error_label: Optional text to describe operation on error.
    :return: list of 'items' objects
    """
    items = resp_object.cgx_content.get('items')

    if resp_object.cgx_status and isinstance(items, list):

        # return data
        return items

    # handle 404 for certian APIs where objects may not exist
    elif resp_object.status_code in [404]:
        return [{}], []

    else:
        if error_label is not None:
            throw_error("Unable to cache {0}.".format(error_label), resp_object)
            return []
        else:
            throw_error("Unable to cache response.".format(error_label), resp_object)
            return []


def diff_tags(list_a, list_b):
    """
    Return human readable diff string of tags changed between two tag lists
    :param list_a: Original tag list
    :param list_b: New tag list
    :return: Difference string
    """
    status_str = text_type("")
    tags_added = [tag for tag in list_b if tag not in list_a]
    tags_removed = [tag for tag in list_a if tag not in list_b]

    if tags_added and tags_removed:
        status_str += "added: {0}".format(text_type(tags_added))
        status_str += " removed: {0}".format(text_type(tags_removed))
    elif tags_added:
        status_str += "added: {0}".format(text_type(tags_added))
    elif tags_removed:
        status_str += "removed: {0}".format(text_type(tags_removed))

    if not status_str:
        status_str = "no changes required."

    return status_str


def check_match(key_name, compiled_pattern, cgx_dict):
    """
    Check match for key/pattern in cgx_dict, return info, but don't modify dict.
    :param key_name: Key name to check
    :param compiled_pattern: Compiled regex to use to check value of key_name cast to text.
    :param cgx_dict: CloudGenix config dict.
    :return: Tuple of Match (bool), 'name' in cgx_dict, and key value checked.
    """
    entry_name = cgx_dict.get("name")

    key_val = cgx_dict.get(key_name)
    if key_val is None:
        # not set, set it to ""
        key_val = ""

    # got key val, cast to string. This will allow regex matching on dict or list subkeys.
    match_string = text_type(key_val)

    # check for REGEX match
    if compiled_pattern.match(match_string):
        return True, entry_name, key_val

    else:
        return False, entry_name, key_val


def check_do_match(the_tag, action, key_name, compiled_pattern, cgx_dict):
    """
    Check match for key/pattern in cgx_dict, modify dict based on action.
    :param the_tag: The tag to add or remove.
    :param action: Action to take with tag if match found
    :param key_name: Key in object to read value from
    :param compiled_pattern: Compiled regex to match value of key_name cast to text.
    :param cgx_dict: CloudGenix config dict
    :return: Tuple of Match (bool), 'name' in cgx_dict, key value checked, and modified CloudGenix config dict.
    """
    entry_name = cgx_dict.get("name")

    key_val = cgx_dict.get(key_name)
    if key_val is None:
        # not set, set it to ""
        key_val = ""

    # got key val, cast to string. This will allow regex matching on dict or list subkeys.
    match_string = text_type(key_val)

    # check for REGEX match
    if compiled_pattern.match(match_string):
        # got a match.
        new_cgx_dict = {}
        if action.lower() == 'add':
            new_cgx_dict = put_tags([the_tag], cgx_dict)
        elif action.lower() == 'remove':
            new_cgx_dict = remove_tags([the_tag], cgx_dict)
        else:
            throw_error("Invalid action: {0}.".format(action))
        return True, entry_name, key_val, new_cgx_dict

    else:
        return False, entry_name, key_val, {}


def parse_basic_objects(sdk, the_tag, action, simulate, object_name, key_name, compiled_pattern, output=None):
    """
    Parse basic API objects based on parameters and add/remove tags based on match(es).
    :param sdk: Authenticated CloudGenix SDK constructor.
    :param the_tag: Tag to add/remove
    :param action: Action to be done on tag (add/remove)
    :param simulate: Bool, is this a simulation only (don't make any changes)
    :param object_name: Object to look up (one of SUPPORTED_OBJECTS)
    :param key_name: Name of key to use in object for matching
    :param compiled_pattern: Compiled regex to match value of key_name cast to text
    :param output: Optional filename to save .csv status to, otherwise will be printed to STDOUT.
    :return: No return
    """
    if object_name.lower() not in SUPPORTED_OBJECTS:
        throw_error("Object {0} not a supported object in this version.")

    if simulate:
        output_results = [["Tag", "Action", "Object Name", "Object Key", "Object Key Value", "Object Match",
                           "Change Detail (Simulated)"]]
    else:
        output_results = [["Tag", "Action", "Object Name", "Object Key", "Object Key Value", "Object Match",
                           "Change Detail"]]

    if object_name == 'sites':
        sites_list = extract_items(sdk.get.sites(), 'sites')

        firstbar = len(sites_list) + 1
        barcount = 1

        print("Working on '{0}'..".format(object_name))

        # could be a long query - start a progress bar.
        pbar = ProgressBar(widgets=[Percentage(), Bar(), ETA()], max_value=firstbar).start()

        for site in list(sites_list):
            site_id = site.get('id')
            match_status, entry_name, key_val, modified_site = check_do_match(the_tag, action,
                                                                              key_name, compiled_pattern, site)

            if match_status:
                if simulate:
                    output_results.append([the_tag, action, entry_name, key_name, key_val,
                                           match_status, diff_tags(extract_tags(site), extract_tags(modified_site))])

                else:
                    # Check if changes needed
                    if diff_tags(extract_tags(site), extract_tags(modified_site)) == 'no changes required.':
                        # No Changes Needed!
                        output_results.append([the_tag, action, entry_name, key_name, key_val,
                                               match_status, diff_tags(extract_tags(site),
                                                                       extract_tags(modified_site))])
                    else:
                        # Need to make changes.
                        site_change_resp = sdk.put.sites(site_id, modified_site)
                        if site_change_resp.cgx_status:
                            output_results.append([the_tag, action, entry_name, key_name, key_val,
                                                   match_status,
                                                   diff_tags(extract_tags(site),
                                                             extract_tags(site_change_resp.cgx_content))])
                        else:
                            throw_warning("'{0}' tag change failed:".format(entry_name), site_change_resp)
            else:
                output_results.append([the_tag, action, entry_name, key_name, key_val,
                                       match_status, None])
            barcount += 1
            pbar.update(barcount)

        # finish after iteration.
        pbar.finish()

    elif object_name == 'elements':
        elements_list = extract_items(sdk.get.elements(), 'elements')

        firstbar = len(elements_list) + 1
        barcount = 1

        print("Working on '{0}'..".format(object_name))

        # could be a long query - start a progress bar.
        pbar = ProgressBar(widgets=[Percentage(), Bar(), ETA()], max_value=firstbar).start()

        for element in list(elements_list):
            element_id = element.get('id')
            match_status, entry_name, key_val, modified_element = check_do_match(the_tag, action,
                                                                                 key_name, compiled_pattern, element)

            # print("PREV TAGS: {0}".format(extract_tags(element)))
            # print("MOD  TAGS: {0}".format(extract_tags(modified_element)))

            if match_status:
                if simulate:
                    output_results.append([the_tag, action, entry_name, key_name, key_val,
                                           match_status, diff_tags(extract_tags(element),
                                                                   extract_tags(modified_element))])

                else:
                    # Check if changes needed
                    if diff_tags(extract_tags(element),
                                 extract_tags(modified_element)) == 'no changes required.':
                        # No Changes Needed!
                        output_results.append([the_tag, action, entry_name, key_name, key_val,
                                               match_status, diff_tags(extract_tags(element),
                                                                       extract_tags(modified_element))])
                    else:
                        # Need to make changes.
                        # clean up element template.
                        for key in dict(modified_element).keys():
                            if key not in ELEMENT_PUT_ITEMS:
                                del modified_element[key]

                        # Add missing elem attributes
                        modified_element['sw_obj'] = None

                        element_change_resp = sdk.put.elements(element_id, modified_element)
                        if element_change_resp.cgx_status:
                            output_results.append([the_tag, action, entry_name, key_name, key_val,
                                                   match_status,
                                                   diff_tags(extract_tags(element),
                                                             extract_tags(element_change_resp.cgx_content))])
                        else:
                            throw_warning("'{0}' tag change failed:".format(entry_name), element_change_resp)
            else:
                output_results.append([the_tag, action, entry_name, key_name, key_val,
                                       match_status, None])
            barcount += 1
            pbar.update(barcount)

        # finish after iteration.
        pbar.finish()

    elif object_name == 'circuitcatagories':
        circuitcatagories_list = extract_items(sdk.get.waninterfacelabels(), 'circuitcatagories')

        firstbar = len(circuitcatagories_list) + 1
        barcount = 1

        print("Working on '{0}'..".format(object_name))

        # could be a long query - start a progress bar.
        pbar = ProgressBar(widgets=[Percentage(), Bar(), ETA()], max_value=firstbar).start()

        for circuitcatagory in list(circuitcatagories_list):
            circuitcatagory_id = circuitcatagory.get('id')
            match_status, entry_name, key_val, modified_circuitcatagory = check_do_match(the_tag, action,
                                                                                         key_name, compiled_pattern,
                                                                                         circuitcatagory)

            if match_status:
                if simulate:
                    output_results.append([the_tag, action, entry_name, key_name, key_val,
                                           match_status, diff_tags(extract_tags(circuitcatagory),
                                                                   extract_tags(modified_circuitcatagory))])

                else:
                    # Check if changes needed
                    if diff_tags(extract_tags(circuitcatagory),
                                 extract_tags(modified_circuitcatagory)) == 'no changes required.':
                        # No Changes Needed!
                        output_results.append([the_tag, action, entry_name, key_name, key_val,
                                               match_status, diff_tags(extract_tags(circuitcatagory),
                                                                       extract_tags(modified_circuitcatagory))])
                    else:
                        # Need to make changes.
                        circuitcatagory_change_resp = sdk.put.waninterfacelabels(circuitcatagory_id,
                                                                                 modified_circuitcatagory)
                        if circuitcatagory_change_resp.cgx_status:
                            output_results.append([the_tag, action, entry_name, key_name, key_val,
                                                   match_status,
                                                   diff_tags(extract_tags(circuitcatagory),
                                                             extract_tags(circuitcatagory_change_resp.cgx_content))])
                        else:
                            throw_warning("'{0}' tag change failed:".format(entry_name), circuitcatagory_change_resp)
            else:
                output_results.append([the_tag, action, entry_name, key_name, key_val,
                                       match_status, None])
            barcount += 1
            pbar.update(barcount)

        # finish after iteration.
        pbar.finish()

        # was output to file specified?
    if output is None:
        # print
        print(tabulate(output_results, headers="firstrow", tablefmt="simple"))
    else:
        with open(output, "w") as csv_output:
            writer = csv.writer(csv_output, quoting=csv.QUOTE_ALL)
            writer.writerows(output_results)


def parse_interfaces(sdk, the_tag, action, simulate, object_name, key_name, compiled_pattern,
                     site_key_name, site_compiled_pattern,
                     element_key_name, element_compiled_pattern, output=None):
    """
    Parse Interfaces API objects based on parameters and add/remove tags based on match(es). Need to match site/element
    at same time - so much more involved.
    :param sdk: Authenticated CloudGenix SDK constructor.
    :param the_tag: Tag to add/remove
    :param action: Action to be done on tag (add/remove)
    :param simulate: Bool, is this a simulation only (don't make any changes)
    :param object_name: Object to look up (one of SUPPORTED_OBJECTS)
    :param key_name: Name of key to use in object for matching
    :param compiled_pattern: Compiled regex to match value of key_name cast to text
    :param site_key_name: Name of key to use in SITE object for matching
    :param site_compiled_pattern: Compiled regex to match value of site_key_name cast to text
    :param element_key_name: Name of key to use in ELEMENT object for matching
    :param element_compiled_pattern: Compiled regex to match value of element_key_name cast to text
    :param output: Optional filename to save .csv status to, otherwise will be printed to STDOUT.
    :return: No Return
    """
    if object_name.lower() not in ['interfaces']:
        throw_error("Object {0} not a supported object in this version.")

    if simulate:
        output_results = [["Tag", "Action", "Site Name", "Site Key", "Site Key Value", "Site Match",
                           "Element Name", "Element Key", "Element Key Value", "Element Match",
                           "Object Name", "Object Key", "Object Key Value", "Object Match",
                           "Change Detail (Simulated)"]]
    else:
        output_results = [["Tag", "Action", "Site Name", "Site Key", "Site Key Value", "Site Match",
                           "Element Name", "Element Key", "Element Key Value", "Element Match",
                           "Object Name", "Object Key", "Object Key Value", "Object Match",
                           "Change Detail"]]

    if object_name == 'interfaces':

        sites_list = extract_items(sdk.get.sites(), 'sites')
        elements_list = extract_items(sdk.get.elements(), 'elements')

        # lookup tables for matches on site id and element id
        site_match_lookup = {}
        element_match_lookup = {}

        # list of lists containing [site_id, element id]
        all_site_element_list = []

        # check site matches, build site match lookup table.
        for site in list(sites_list):
            site_id = site.get('id')
            site_match_status, site_entry_name, site_key_val, = check_match(site_key_name, site_compiled_pattern, site)

            site_match_lookup[site_id] = {
                "site_entry_name": site_entry_name,
                "site_key_val": site_key_val,
                "site_match_status": site_match_status
            }

        # check element matches, build element match lookup table.
        for element in list(elements_list):
            element_id = element.get('id')
            element_site_id = element.get('site_id')

            # add to all site->element iteration list
            if element_id and element_site_id:
                all_site_element_list.append([element_site_id, element_id])

            # check for match.
            element_match_status, element_entry_name, element_key_val, = check_match(element_key_name,
                                                                                     element_compiled_pattern, element)

            element_match_lookup[element_id] = {
                "element_entry_name": element_entry_name,
                "element_key_val": element_key_val,
                "element_match_status": element_match_status
            }

        # Great, now we have max objects that can be queried. Set status bar
        firstbar = len(all_site_element_list) + 1
        barcount = 1

        print("Working on 'interfaces'..")

        # could be a long query - start a progress bar.
        pbar = ProgressBar(widgets=[Percentage(), Bar(), ETA()], max_value=firstbar).start()

        for site_id_element_id_list in all_site_element_list:
            site_id = site_id_element_id_list[0]
            element_id = site_id_element_id_list[1]

            site_lookup = site_match_lookup.get(site_id)
            element_lookup = element_match_lookup.get(element_id)

            if site_id == "1":
                # site id 1 = unassigned. Silently skip, as can't modify interfaces for unassigned elements.
                barcount += 1
                pbar.update(barcount)
                continue
            if site_lookup is None:
                # error, these should not be missing. Throw warning.
                throw_warning("Unable to read site match data for site_id {0}. Skipping.".format(site_id))
                barcount += 1
                pbar.update(barcount)
                continue
            elif element_lookup is None:
                # error, these should not be missing. Throw warning.
                throw_warning("Unable to read element match data for element_id {0}. Skipping.".format(element_id))
                barcount += 1
                pbar.update(barcount)
                continue

            # get all of the saved match info.
            site_entry_name = site_lookup["site_entry_name"]
            site_key_val = site_lookup["site_key_val"]
            site_match_status = site_lookup["site_match_status"]
            element_entry_name = element_lookup["element_entry_name"]
            element_key_val = element_lookup["element_key_val"]
            element_match_status = element_lookup["element_match_status"]

            if site_match_status and element_match_status:
                # need to iterate and check interfaces.
                interfaces_list = extract_items(sdk.get.interfaces(site_id, element_id), 'interfaces')

                for interface in list(interfaces_list):
                    interface_id = interface.get('id')

                    match_status, entry_name, key_val, modified_interface = check_do_match(the_tag, action,
                                                                                           key_name, compiled_pattern,
                                                                                           interface)

                    # need to handle 'controller 2' port, which can't currently be modified.
                    if entry_name == 'controller 2':
                        # have to silently skip, can't modify controller 2.
                        continue

                    if match_status:
                        if simulate:
                            output_results.append([the_tag, action, site_entry_name, site_key_name, site_key_val,
                                                   site_match_status, element_entry_name, element_key_name,
                                                   element_key_val, element_match_status, entry_name, key_name, key_val,
                                                   match_status, diff_tags(extract_tags(interface),
                                                                           extract_tags(modified_interface))])

                        else:
                            # Check if changes needed
                            if diff_tags(extract_tags(interface),
                                         extract_tags(modified_interface)) == 'no changes required.':
                                # Don't need to submit, tags are already correct.
                                output_results.append([the_tag, action, site_entry_name, site_key_name, site_key_val,
                                                       site_match_status, element_entry_name, element_key_name,
                                                       element_key_val, element_match_status, entry_name, key_name,
                                                       key_val,
                                                       match_status, diff_tags(extract_tags(interface),
                                                                               extract_tags(modified_interface))])

                            else:
                                # need to make changes!
                                interface_change_resp = sdk.put.interfaces(site_id, element_id, interface_id,
                                                                           modified_interface)
                                if interface_change_resp.cgx_status:
                                    output_results.append([the_tag, action, site_entry_name, site_key_name,
                                                           site_key_val, site_match_status, element_entry_name,
                                                           element_key_name, element_key_val, element_match_status,
                                                           entry_name, key_name, key_val, match_status,
                                                           diff_tags(extract_tags(interface),
                                                                     extract_tags(interface_change_resp.cgx_content))])

                                else:
                                    throw_warning("'{0}' tag change failed:".format(entry_name), interface_change_resp)
                    else:
                        # no match on Interface.
                        output_results.append([the_tag, action, site_entry_name, site_key_name, site_key_val,
                                               site_match_status, element_entry_name, element_key_name,
                                               element_key_val, element_match_status, entry_name, key_name, key_val,
                                               match_status, None])

            else:
                # no match, just update output.
                output_results.append([the_tag, action, site_entry_name, site_key_name, site_key_val, site_match_status,
                                       element_entry_name, element_key_name, element_key_val, element_match_status,
                                       None, None, None, None, None])

            # finished this site_id/element_id pair. next.
            barcount += 1
            pbar.update(barcount)

        # finish after iteration.
        pbar.finish()

    # was output to file specified?
    if output is None:
        # print
        print(tabulate(output_results, headers="firstrow", tablefmt="simple"))
    else:
        with open(output, "w") as csv_output:
            writer = csv.writer(csv_output, quoting=csv.QUOTE_ALL)
            writer.writerows(output_results)


####
#
# End custom modifiable code
#
####


# Start the script.
def go():
    """
    Stub script entry point. Authenticates CloudGenix SDK, and gathers options from command line to run do_site()
    :return: No return
    """

    # Parse arguments
    parser = argparse.ArgumentParser(description="{0} ({1})".format(GLOBAL_MY_SCRIPT_NAME, GLOBAL_MY_SCRIPT_VERSION))

    ####
    #
    # Add custom cmdline argparse arguments here
    #
    ####

    action_group = parser.add_argument_group('Action', 'Add or Remove Tags')
    action = action_group.add_mutually_exclusive_group(required=True)
    action.add_argument('--add', '-A', action='store_true', default=False)
    action.add_argument('--remove', '-R', action='store_true', default=False)
    action_group.add_argument('--simulate', '-S', action='store_true', default=False,
                              help="Simulate and display prospective changes. Don't make any actual modifications.")
    action_group.add_argument('--tag', '-T', type=text_type, required=True,
                              help='Tag to add or remove from objects.')
    action_group.add_argument('--object', '-O', type=text_type, required=True,
                              help="Object to add/remove tags from. One of {0}.".format(", ".join(SUPPORTED_OBJECTS)))

    action_group.add_argument('--interfaces-site-key', '-SK', type=text_type, default='name',
                              help="Key in Site object to use for inclusion ('interfaces' only). Default 'name'")
    action_group.add_argument('--interfaces-element-key', '-EK', type=text_type, default='name',
                              help="Key in Element object to use for inclusion ('interfaces' only). Default 'name'")
    action_group.add_argument('--key', '-K', type=text_type, default='name',
                              help="Key in object to use for match. Default 'name'.")

    action_group.add_argument('--interfaces-site-pattern', '-SP', type=text_type, default='.*',
                              help="REGEX Pattern to match Site Object with for inclusion ('interfaces' only)."
                                   " Default '.*'")
    action_group.add_argument('--interfaces-element-pattern', '-EP', type=text_type, default='.*',
                              help="REGEX Pattern to match Element Object with for inclusion ('interfaces' only)."
                                   " Default '.*'")
    action_group.add_argument('--pattern', '-P', type=text_type, required=True,
                              help="REGEX Pattern to match Object Key value with.")
    action_group.add_argument('--output', type=text_type, default=None,
                              help="Output to filename. If not specified, will print output on STDOUT.")

    ####
    #
    # End custom cmdline arguments
    #
    ####

    # Standard CloudGenix script switches.
    controller_group = parser.add_argument_group('API', 'These options change how this program connects to the API.')
    controller_group.add_argument("--controller", "-C",
                                  help="Controller URI, ex. https://api.elcapitan.cloudgenix.com",
                                  default=None)

    login_group = parser.add_argument_group('Login', 'These options allow skipping of interactive login')
    login_group.add_argument("--email", "-E", help="Use this email as User Name instead of cloudgenix_settings.py "
                                                   "or prompting",
                             default=None)
    login_group.add_argument("--password", "-PW", help="Use this Password instead of cloudgenix_settings.py "
                                                       "or prompting",
                             default=None)
    login_group.add_argument("--insecure", "-I", help="Do not verify SSL certificate",
                             action='store_true',
                             default=False)
    login_group.add_argument("--noregion", "-NR", help="Ignore Region-based redirection.",
                             dest='ignore_region', action='store_true', default=False)

    debug_group = parser.add_argument_group('Debug', 'These options enable debugging output')
    debug_group.add_argument("--sdkdebug", "-D", help="Enable SDK Debug output, levels 0-2", type=int,
                             default=0)

    args = vars(parser.parse_args())

    sdk_debuglevel = args["sdkdebug"]

    # Build SDK Constructor
    if args['controller'] and args['insecure']:
        sdk = cloudgenix.API(controller=args['controller'], ssl_verify=False)
    elif args['controller']:
        sdk = cloudgenix.API(controller=args['controller'])
    elif args['insecure']:
        sdk = cloudgenix.API(ssl_verify=False)
    else:
        sdk = cloudgenix.API()

    # check for region ignore
    if args['ignore_region']:
        sdk.ignore_region = True

    # SDK debug, default = 0
    # 0 = logger handlers removed, critical only
    # 1 = logger info messages
    # 2 = logger debug messages.

    if sdk_debuglevel == 1:
        # CG SDK info
        sdk.set_debug(1)
    elif sdk_debuglevel >= 2:
        # CG SDK debug
        sdk.set_debug(2)

    # login logic. Use cmdline if set, use AUTH_TOKEN next, finally user/pass from config file, then prompt.
    # figure out user
    if args["email"]:
        user_email = args["email"]
    elif CLOUDGENIX_USER:
        user_email = CLOUDGENIX_USER
    else:
        user_email = None

    # figure out password
    if args["password"]:
        user_password = args["password"]
    elif CLOUDGENIX_PASSWORD:
        user_password = CLOUDGENIX_PASSWORD
    else:
        user_password = None

    # check for token
    if CLOUDGENIX_AUTH_TOKEN and not args["email"] and not args["password"]:
        sdk.interactive.use_token(CLOUDGENIX_AUTH_TOKEN)
        if sdk.tenant_id is None:
            raise CloudGenixTaggerError("AUTH_TOKEN login failure, please check token.")

    else:
        while sdk.tenant_id is None:
            sdk.interactive.login(user_email, user_password)
            # clear after one failed login, force relogin.
            if not sdk.tenant_id:
                user_email = None
                user_password = None

    ####
    #
    # Do your custom work here, or call custom functions.
    #
    ####

    args_action = None
    if args['add']:
        args_action = 'add'
    elif args['remove']:
        args_action = 'remove'

    # interfaces requires hierarchical matching.
    if args['object'].lower() == 'interfaces':
        parse_interfaces(sdk, args['tag'], args_action, args['simulate'], args['object'], args['key'],
                         re.compile(args['pattern']), args['interfaces_site_key'],
                         re.compile(args['interfaces_site_pattern']), args['interfaces_element_key'],
                         re.compile(args['interfaces_element_pattern']),
                         output=args['output'])
    else:
        parse_basic_objects(sdk, args['tag'], args_action, args['simulate'], args['object'], args['key'],
                            re.compile(args['pattern']), output=args['output'])

    ####
    #
    # End custom work.
    #
    ####


if __name__ == "__main__":
    go()
