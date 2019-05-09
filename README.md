CloudGenix Tagger
----------

#### Synopsis
Utility to manage tags across a large number of CloudGenix sites, elements, interfaces, and Circuit Catagories.

#### Features
TBD

#### Requirements
* Active CloudGenix Account
* Python >= 2.7 or >=3.6
* Python modules:
    * CloudGenix Python SDK >= 5.1.1b1 - <https://github.com/CloudGenix/sdk-python>

#### License
MIT

#### Installation:
 - **PIP:** `pip install cloudgenix_tagger`. After install, `do_tag`. Scripts should be placed in the Python
 Scripts directory. 
 - **Github:** Download files to a local directory, manually run `do_tag.py` script. 

### Examples of usage:
 1. Add tag "Aaron_Likes_tags" to all sites with "Name" starting with "AUTO"
    ```bash
    edwards-mbp-pro:cloudgenix_tagger aaron$ ./do_tags.py -T "Aaron_Likes_tags" -O sites -P "^AUTO.*" -A
    Working on 'sites'..
    100%|############################################################################################################################################################################################################################################################################################################################################################################################################|Time:  0:00:00
    Tag               Action    Object Name             Object Key    Object Key Value        Object Match    Change Detail
    ----------------  --------  ----------------------  ------------  ----------------------  --------------  ---------------------------
    Aaron_Likes_tags  add       AUTOMATION-LAB          name          AUTOMATION-LAB          True            added: ['Aaron_Likes_tags']
    Aaron_Likes_tags  add       Azure Central US        name          Azure Central US        False
    Aaron_Likes_tags  add       Chicago Branch 2        name          Chicago Branch 2        False
    Aaron_Likes_tags  add       New York Branch 1       name          New York Branch 1       False
    Aaron_Likes_tags  add       Oracle DC               name          Oracle DC               False
    Aaron_Likes_tags  add       Orange-Test             name          Orange-Test             False
    Aaron_Likes_tags  add       San Francisco DC 1      name          San Francisco DC 1      False
    Aaron_Likes_tags  add       Seattle Branch 3        name          Seattle Branch 3        False
    Aaron_Likes_tags  add       Washington D.C. - DC 2  name          Washington D.C. - DC 2  False
    Aaron_Likes_tags  add       test                    name          test                    False
    edwards-mbp-pro:cloudgenix_tagger aaron$ 
    ```
 2. Remove tag "Aaron_Likes_tags" from all sites.
    ```bash
    edwards-mbp-pro:cloudgenix_tagger aaron$ ./do_tags.py -T "Aaron_Likes_tags" -O sites -P ".*" -R
    Working on 'sites'..
    100%|############################################################################################################################################################################################################################################################################################################################################################################################################|Time:  0:00:00
    Tag               Action    Object Name             Object Key    Object Key Value        Object Match    Change Detail
    ----------------  --------  ----------------------  ------------  ----------------------  --------------  -----------------------------
    Aaron_Likes_tags  remove    AUTOMATION-LAB          name          AUTOMATION-LAB          True            removed: ['Aaron_Likes_tags']
    Aaron_Likes_tags  remove    Azure Central US        name          Azure Central US        True            no changes required.
    Aaron_Likes_tags  remove    Chicago Branch 2        name          Chicago Branch 2        True            no changes required.
    Aaron_Likes_tags  remove    New York Branch 1       name          New York Branch 1       True            no changes required.
    Aaron_Likes_tags  remove    Oracle DC               name          Oracle DC               True            no changes required.
    Aaron_Likes_tags  remove    Orange-Test             name          Orange-Test             True            no changes required.
    Aaron_Likes_tags  remove    San Francisco DC 1      name          San Francisco DC 1      True            no changes required.
    Aaron_Likes_tags  remove    Seattle Branch 3        name          Seattle Branch 3        True            no changes required.
    Aaron_Likes_tags  remove    Washington D.C. - DC 2  name          Washington D.C. - DC 2  True            no changes required.
    Aaron_Likes_tags  remove    test                    name          test                    True            no changes required.
    edwards-mbp-pro:cloudgenix_tagger aaron$ 

    ```
 
### Caveats and known issues:
 - None
 
#### Version
| Version | Build | Changes |
| ------- | ----- | ------- |
| **1.0.0** | **b1** | Initial Release. |

#### Command line help
```bash
edwards-mbp-pro:cloudgenix_tagger aaron$ ./do_tags.py -h
usage: do_tags.py [-h] (--add | --remove) [--simulate] --tag TAG --object
                  OBJECT [--interfaces-site-key INTERFACES_SITE_KEY]
                  [--interfaces-element-key INTERFACES_ELEMENT_KEY]
                  [--key KEY]
                  [--interfaces-site-pattern INTERFACES_SITE_PATTERN]
                  [--interfaces-element-pattern INTERFACES_ELEMENT_PATTERN]
                  --pattern PATTERN [--output OUTPUT]
                  [--controller CONTROLLER] [--email EMAIL]
                  [--password PASSWORD] [--insecure] [--noregion]
                  [--sdkdebug SDKDEBUG]

CloudGenix Tagger (v1.0.0)

optional arguments:
  -h, --help            show this help message and exit

Action:
  Add or Remove Tags

  --add, -A
  --remove, -R
  --simulate, -S        Simulate and display prospective changes. Don't make
                        any actual modifications.
  --tag TAG, -T TAG     Tag to add or remove from objects.
  --object OBJECT, -O OBJECT
                        Object to add/remove tags from. One of sites,
                        elements, interfaces, circuitcatagories.
  --interfaces-site-key INTERFACES_SITE_KEY, -SK INTERFACES_SITE_KEY
                        Key in Site object to use for inclusion ('interfaces'
                        only). Default 'name'
  --interfaces-element-key INTERFACES_ELEMENT_KEY, -EK INTERFACES_ELEMENT_KEY
                        Key in Element object to use for inclusion
                        ('interfaces' only). Default 'name'
  --key KEY, -K KEY     Key in object to use for match. Default 'name'.
  --interfaces-site-pattern INTERFACES_SITE_PATTERN, -SP INTERFACES_SITE_PATTERN
                        REGEX Pattern to match Site Object with for inclusion
                        ('interfaces' only). Default '.*'
  --interfaces-element-pattern INTERFACES_ELEMENT_PATTERN, -EP INTERFACES_ELEMENT_PATTERN
                        REGEX Pattern to match Element Object with for
                        inclusion ('interfaces' only). Default '.*'
  --pattern PATTERN, -P PATTERN
                        REGEX Pattern to match Object Key value with.
  --output OUTPUT       Output to filename. If not specified, will print
                        output on STDOUT.

API:
  These options change how this program connects to the API.

  --controller CONTROLLER, -C CONTROLLER
                        Controller URI, ex.
                        https://api.elcapitan.cloudgenix.com

Login:
  These options allow skipping of interactive login

  --email EMAIL, -E EMAIL
                        Use this email as User Name instead of
                        cloudgenix_settings.py or prompting
  --password PASSWORD, -PW PASSWORD
                        Use this Password instead of cloudgenix_settings.py or
                        prompting
  --insecure, -I        Do not verify SSL certificate
  --noregion, -NR       Ignore Region-based redirection.

Debug:
  These options enable debugging output

  --sdkdebug SDKDEBUG, -D SDKDEBUG
                        Enable SDK Debug output, levels 0-2
edwards-mbp-pro:cloudgenix_tagger aaron$ 
```
