"""
brainregister

A Package that defines a 3D image registeration framework, including optimised
registration parameters and the Allen CCFv3 mouse brian atlas.

"""

# package metadata
__version__ = '0.1.0'
__author__ = 'Steven J. West'

# package imports
import os
import glob
import sys
import gc
import yaml # pyyaml library
from pathlib import Path
import SimpleITK as sitk #SimpleITK-elastix package

 # get the module directory - to point to resources/ and other package artifacts
BRAINREGISTER_MODULE_DIR = os.path.abspath( os.path.dirname(__file__) )


# example function for testing
def version():
    print("BrainRegister : version "+__version__)
    print("  Author : "+__author__)


def create_brainregister_parameters_file(sample_template_path, 
            output_dir = Path('brainregister'),
            brainregister_params_template_path = 'brainregister_params', 
            brainregister_params_filename = 'brainregister_parameters.yaml'):
    '''Create Brainregister Parameters File

    Generates a new brainregister_parameters.yaml file based on the
    sample_template_path: this should be a RELATIVE PATH to an existing VALID
    IMAGE which will be used for elastix registration.
    
    The brainregister_parameters.yaml file will also be filled with any other
    Sample Images (files with the same extension as the Sample Template Image)
    for transformation.
    
    The brainregister_parameters.yaml file will be written to disk to output_dir
    which defines a DIR tree from the CURRENT WORKING DIRECTORY that will be
    created for holding registration data.
    
    Prior to registration, the user should review the 
    brainregister_parameters.yaml file and modify as appropriate.
    
    To execute the registration use 
    brainregister.register(brainregister_parameters.yaml)
    
    Parameters
    ----------
    sample_template_path : pathlib Path
        This should point to the image file that will serve as the sample-
        template (the image upon which the registration will be optimised).
    
    output_dir : pathlib Path
        This points to the output dir where all brainregister registration and
        transformation data will be stored.  set to 'brainregister' by default
        and written to the current working directory.
    
    brainregister_params_template_path : str
        String representing the path to the template brainregister parameters 
        yaml file.  Set to 'brainregister_params' by default, so will use the 
        built-in brainregister allen ccf data.  This can be set to an 
        external template by the user.  NOTE: This function assumes any 
        user-defined yaml template  contains the SAME FIELDS, but has modified 
        default values to suit the users needs.  Any comments in an external 
        yaml parameters file will be REMOVED after parsing through this method,
        therefore it is best to create/copy a user-defined template manually.
    
    brainregister_params_filename : str
        String representing the file name the brainregister parameters yaml file
        will be written to.  Set to 'brainregister_parameters.yaml' by default 
        - RECOMMENDED TO KEEP THIS NAMING CONVENTION!
    
    Returns
    -------
    brp : dict
        BrainRegister Parameters dict.

    '''
    
    # RESOLVE the path- remove any .. references and convert to absolute path
    sample_template_path_res = sample_template_path.resolve()
    
    # Make the path into an absolute path - remove ~ and ensure absolute
    # AND convert to STRING
    stp = str(sample_template_path.expanduser().absolute() )
    
    # try to read image header with sitk
    reader = sitk.ImageFileReader()
    reader.SetFileName( stp )
    reader.LoadPrivateTagsOn()
    try:
        reader.ReadImageInformation()
    except:
        print('The input file is not a valid image: ', stp)
        sys.exit('input file not valid')
    
    # if image is valid to sitk.reader this will pass
    
    # next - resolve and create output_dir
    output_dir.resolve().mkdir(parents=True, exist_ok=True)
    # this is where the brainregister_parameters.yaml file will be written
    brainregister_params_path = Path( 
        str(output_dir.resolve().expanduser().absolute() ) 
        + os.path.sep
        + brainregister_params_filename)
    
    # next - build the yaml file
    if brainregister_params_template_path == 'brainregister_params':
        # open the brainregister template from resources/ dir in brainregister package
        # read yaml to dict
        br_params = os.path.join(
                        BRAINREGISTER_MODULE_DIR, 
                        'resources', 'brainregister_parameters.yaml')
        with open(br_params, 'r') as file:
            brp = yaml.safe_load(file)
        
        # read yaml to list - THIS CONTAINS THE COMMENTS
        with open(br_params, 'r') as file:
            brpf = file.readlines()
    else:
        with open(brainregister_params_template_path, 'r') as file:
            brp = yaml.safe_load(file)
    
    
    # MODIFY PARAMETERS
    
    # set sample-template-path to stp
    brp['sample-template-path'] = os.path.relpath(
                sample_template_path_res, 
                output_dir.resolve().expanduser().absolute()  )
    
    # get other files with same suffix as stp in parent dir
    fn, ext = os.path.splitext(sample_template_path_res.name)
    files = glob.glob( 
        str( str(sample_template_path_res.parent.expanduser().absolute() ) 
            + os.path.sep 
            + "*" 
            + ext) )
    # filter to remove the current sample_template_path and extract just the name(s)
    filenames = [Path(f).name for f in files if f != str(sample_template_path_res.expanduser().absolute()) ]
    
    brp['sample-images'] = filenames
    
    # set output dirs to parent of sample-template - NOT NEEDED NOW as set correctly by default
    #brp['downsampled-stacks-path'] = str(
    #    str(sample_template_path.parent.expanduser().absolute() ) + 
    #          os.path.sep + 'downsample_stacks')
    
    #brp['ccf-to-sample-path'] = str(
    #    str(sample_template_path.parent.expanduser().absolute() ) + 
    #          os.path.sep + 'ccf_to_sample')
    
    #brp['sample-to-ccf-path'] = str(
    #    str(sample_template_path.parent.expanduser().absolute() ) + 
    #          os.path.sep + 'sample_to_ccf')
    
    # write to yaml file
    with open(brainregister_params_path, 'w') as file:
        yaml.dump(brp, file, sort_keys=False)
    
    # ONLY IF USING brainregister parameters yaml (as know where comments are!)
    if brainregister_params_template_path == 'brainregister_params':
        # add COMMENTS from original file
        with open(brainregister_params_path, 'r') as file:
            brpf2 = file.readlines()
        
        # get index of sample-template-orientation 
         # as sample-images length can VARY!
        sil = [i for i, s in enumerate(brpf2) if 'sample-template-orientation' in s]
        
        # get index of downsampled-to-ccf-save-images
         # as downsampled-to-ccf-parameters-files length can VARY!
        pfld = [i for i, s in enumerate(brpf2) if 'downsampled-to-ccf-save-images' in s]
        
        # get index of ccf-to-downsampled-save-annotation
         # as ccf-to-downsampled-parameters-files length can VARY!
        pflc = [i for i, s in enumerate(brpf2) if 'ccf-to-downsampled-save-annotation' in s]
        
        # concat comments and yaml lines into one list:
        brpf3 = [ brpf[0:23] + # sample-template comments
                  brpf2[ 0:(sil[0]+1) ] + # sample-template data
                  brpf[33:49] + # fullstack-to-downsampled comments
                  brpf2[ (sil[0]+1):(sil[0]+9)] + # fullstack-to-downsampled data
                  brpf[57:69] + # downsampled-to-fullstack comments
                  brpf2[ (sil[0]+9):(sil[0]+15)] + # downsampled-to-fullstack data
                  brpf[75:90] + # downsampled-to-ccf comments
                  brpf2[(sil[0]+15):(pfld[0]+3)] + # downsampled-to-ccf data
                  brpf[100:113] + # ccf-to-downsampled comments
                  brpf2[(pfld[0]+3):(pflc[0]+3)] # ccf-to-downsampled data
                                                          ]
        brpf3 = brpf3[0] # remove the nesting of this list
        
        # write this OVER the current yaml
        with open(brainregister_params_path, 'w') as file:
            for b in brpf3:
                file.write('%s' % b)
        
        print('  written brainregister_parameters.yaml file to : ') 
        print('    ', os.path.relpath(
                brainregister_params_path, 
                os.getcwd()  ) )
    else:
        print('  written custom brainregister parameters yaml file', brainregister_params_template_path)
    
    # return the yaml file dict
    return brp
    



class BrainRegister(object):
    
    
    def __init__(self, yaml_path):
        
        self.set_brainregister_parameters_filepath(yaml_path)
        self.initialise_brainregister()
        self.create_output_dirs()
    
    
    
    def set_brainregister_parameters_filepath(self, yaml_path):
        self.yaml_path = yaml_path
        
    
    
    def get_brainregister_parameters_Filepath(self):
        return self.yaml_path
    
    
    def register(self):
        
        self.register_transform_fullstack_to_downsampled()
        
        self.register_downsampled_to_ccf()
        self.transform_downsampled_to_ccf()
        
        self.register_ccf_to_downsampled()
        self.transform_ccf_to_downsampled()
        
        self.transform_downsampled_to_fullstack()
    
    
    
    def initialise_brainregister(self):
        
        print('')
        print('')
        print('==========================')
        print('INITIALISING BRAINREGISTER')
        print('==========================')
        print('')
        
        print('  loading brainregister parameters file..')
        self.load_params()
        
        
        ### RESOLVE PARAMETERS ###
        ##########################
        
        # paths to output DIRs
        print('  resolving output DIR paths..')
        self.resolve_dirs()
        
        # paths to sample template and sample images
        print('  resolving sample template and image paths..')
        self.resolve_image_paths()
        
        
        print('  resolving parameter file paths..')
        self.resolve_param_paths()
        
        # paths to ccf params and ccf template + annotation imagess
        print('  resolving ccf template and annotation paths..')
        self.resolve_ccf_params()
        
        print('')
        
    
    
    
    
    def load_params(self):
        """
        Load brainregister parameters file
        
        This loads the brainregister_parameters.yaml file pointed to by yaml_file,
        and the brainregister_parameters.yaml directory path. These are set to
        instance variables brp and brp_dir, respectively.
        
        This function must be run before any other processing can take place!
        """
        
        # resolve path to parameters file and get the parent dir
        yaml_path_res = Path(self.yaml_path).resolve()
        self.brp_dir = yaml_path_res.parent
        
        # first check that yaml_path is valid and read file
        if Path(self.yaml_path).exists() == False:
            print('')
            print('xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx')
            print('')
            sys.exit('  no brainregister_params file!')
        
        with open(self.yaml_path, 'r') as file:
            self.brp = yaml.safe_load(file)
        
        # check the resolutions have been set to something other than 0.0 (which is the default)
        if ( (self.brp['sample-template-resolution']['x-um'] == 0.0) | 
            (self.brp['sample-template-resolution']['y-um'] == 0.0) | 
            (self.brp['sample-template-resolution']['z-um'] == 0.0) ) :
            print('')
            print('')
            sys.exit( str('ERROR :  image resolution not set in brainregister_params : ' + 
                      self.yaml_path) )
        
        
    
    
    def resolve_dirs(self):
        '''
        Resolve the output directory paths

        Returns
        -------
        None.

        '''
        
        self.ds_fs_dir = Path( str(self.brp_dir) 
                       + os.path.sep
                       + self.brp['downsampled-to-fullstack-path'] )
        
        self.fs_ds_dir = Path( str(self.brp_dir) 
                       + os.path.sep
                       + self.brp['fullstack-to-downsampled-path'] )
        
        self.ds_ccf_dir = Path( str(self.brp_dir) 
                       + os.path.sep
                       + self.brp['downsampled-to-ccf-path'] )
        
        self.ccf_ds_dir = Path( str(self.brp_dir) 
                       + os.path.sep
                       + self.brp['ccf-to-downsampled-path'] )
        
        
    
    
    def resolve_image_paths(self):
        '''
        Resolve the sample image paths
        
        Also instantiate object variables for sample template image in fullstack,
        downsampled, and ccf spaces - initially set to None.

        Returns
        -------
        None.

        '''
        
        # sample template path
        self.template_path = Path( 
            str(self.brp_dir) + 
            os.path.sep + 
            self.brp['sample-template-path'] ).resolve()
        
        
        self.template_path_ds = Path( 
            str(self.fs_ds_dir) + 
            os.path.sep  + 
            self.brp['fullstack-to-downsampled-prefix'] + 
            Path(os.path.basename(
                            self.brp['sample-template-path'])).stem + 
            '.' + 
            self.brp['fullstack-to-downsampled-save-image-type'] )
        
        self.template_path_ds_ccf = Path( 
            str(self.ds_ccf_dir) + 
            os.path.sep  + 
            self.brp['downsampled-to-ccf-prefix'] + 
            self.brp['fullstack-to-downsampled-prefix'] + 
            Path(os.path.basename(
                            self.brp['sample-template-path'])).stem +
            '.' + 
            self.brp['downsampled-to-ccf-save-image-type'] )
        
        
        # sample images paths - only if not lbank
        if not self.brp['sample-images']:
            # empty list - no additional images
            self.sample_images = []
            self.sample_images_ds = []
            self.sample_images_ds_ccf = []
        else:
            
            self.sample_images = [Path( 
                str(self.template_path.parent) 
                + os.path.sep 
                + str(s)) for s in self.brp['sample-images'] ]
            
            self.sample_images_ds = [Path( 
            str(self.fs_ds_dir) + 
            os.path.sep  + 
            self.brp['fullstack-to-downsampled-prefix'] + 
            Path(os.path.basename(s)).stem +
            '.' + 
            self.brp['fullstack-to-downsampled-save-image-type'] ) for s in self.brp['sample-images'] ]
            
            self.sample_images_ds_ccf = [Path( 
            str(self.ds_ccf_dir) + 
            os.path.sep  + 
            self.brp['downsampled-to-ccf-prefix'] + 
            self.brp['fullstack-to-downsampled-prefix'] + 
            Path(os.path.basename(s)).stem +
            '.' + 
            self.brp['downsampled-to-ccf-save-image-type'] ) for s in self.brp['sample-images'] ]
        
        # ALSO set all image instance variables to None
        self.template_img = None
        self.template_ds_img = None
        self.template_ds_img_filt = None
        self.template_ds_ccf_img = None
        
        
    
    
    
    
    def resolve_param_paths(self):
        '''
        Resolve elastix and transformix parameters files paths
        
        Also instantiate object variables : booleans for ds/ccf prefiltering 
        status, and parameter maps for fullstack <-> downsampled, and 
        downsampled <-> ccf.

        Returns
        -------
        None.

        '''
        
        self.wd = Path(os.getcwd()).resolve() # store current working directory
        
        self.fs_ds_pm_path = [ Path(os.path.join( 
            self.fs_ds_dir, 
             self.brp['fullstack-to-downsampled-transform-params-filename'] ) ) ]
        
        self.ds_fs_pm_path = [ Path( os.path.join( 
            self.ds_fs_dir, 
             self.brp['downsampled-to-fullstack-transform-params-filename'] ) ) ]
        
        
        self.ds_ccf_pm_paths = []
        for pm in self.brp['downsampled-to-ccf-transform-params-filenames']:
            self.ds_ccf_pm_paths.append( 
                Path( os.path.join(self.ds_ccf_dir, pm ) ) )
        
        self.ccf_ds_pm_paths = []
        for pm in self.brp['ccf-to-downsampled-transform-params-filenames']:
            self.ccf_ds_pm_paths.append( 
                Path( os.path.join( self.ccf_ds_dir, pm ) ) )
        
        # check params-filenames and files are of the same number
        if (len(self.brp['downsampled-to-ccf-transform-params-filenames']) != 
            len(self.brp['downsampled-to-ccf-parameters-files'])):
            sys.exit('  ERROR - downsampled-to-ccf : transform-params-filenames'+
                 ' and parameters-files are not equal in length')
        
        if (len(self.brp['ccf-to-downsampled-transform-params-filenames']) != 
            len(self.brp['ccf-to-downsampled-parameters-files'])):
            sys.exit('  ERROR - ccf-to-downsampled : transform-params-filenames'+
                 ' and parameters-files are not equal in length')
        
        self.ds_ccf_ep = self.get_elastix_params(self.brp['downsampled-to-ccf-parameters-files'])
        self.ccf_ds_ep = self.get_elastix_params(self.brp['ccf-to-downsampled-parameters-files'])
        
        self.ds_ccf_prefiltered = False # set to True once ds and ccf templates has been prefiltered
        self.ccf_ds_prefiltered = False # set to True once ds and ccf templates has been prefiltered
        
        # load the parameter map lists if they exist, or set to None
        self.fs_ds_pm = self.load_pm_files(self.fs_ds_pm_path)#self.load_fs_ds_tp_file()
        self.ds_fs_pm = self.load_pm_files(self.ds_fs_pm_path)#self.load_ds_fs_tp_file()
        self.ds_fs_pm_anno = self.edit_pms_nearest_neighbour(self.ds_fs_pm)
        self.ds_ccf_pm = self.load_pm_files(self.ds_ccf_pm_paths)
        self.ccf_ds_pm = self.load_pm_files(self.ccf_ds_pm_paths)
        self.ccf_ds_pm_anno = self.edit_pms_nearest_neighbour(self.ccf_ds_pm)

    
    
    
    def resolve_ccf_params(self):
        '''
        Resolve the CCF
        
        Load the CCF yaml parameters file, and resolve the path to the CCF 
        template image.
        
        Also instantiate object variables for ccf template and annotation image 
        in ccf, downsampled, and fullstack spaces - initially set to None.

        Returns
        -------
        None.

        '''
        
        if self.brp['fullstack-to-downsampled-ccf-path'] == 'brainregister_allen_ccf':
            # open the brainregister ccf params file
              # from resources/allen-ccf/ dir in brainregister package
            # read yaml to dict
            ccf_params = os.path.join(BRAINREGISTER_MODULE_DIR, 'resources',
                                      'allen-ccf', 'ccf_parameters.yaml')
            with open(ccf_params, 'r') as file:
                self.ccfp = yaml.safe_load(file)
            
        else: # use user-defined path
            with open( os.path.join(self.brp['fullstack-to-downsampled-ccf-path'], 
                                    'ccf_parameters.yaml'), 'r') as file:
                self.ccfp = yaml.safe_load( file )
        
        #print('  loading ccf template image..')
        # read the ccf template and ccf annotation
        self.ccf_template_path = Path( str(
            os.path.join(
                os.path.dirname(ccf_params),
                self.ccfp['ccf-template-path']
                ) 
            ) 
         )
        
        #print('  loading ccf annotation image..')
        self.ccf_annotation_path =  Path( str(
            os.path.join(
                os.path.dirname(ccf_params),
                self.ccfp['ccf-annotation-path']
                ) 
            ) 
         )
        
        
        self.ccf_template_path_ds = Path( 
            str(self.ccf_ds_dir) + 
            os.path.sep  + 
            self.brp['ccf-to-downsampled-prefix'] + 
            Path(os.path.basename(
                            self.ccfp['ccf-template-path'])).stem +
            '.' + 
            self.brp['ccf-to-downsampled-save-image-type'] )
        
        self.ccf_annotation_path_ds = Path( 
            str(self.ccf_ds_dir) + 
            os.path.sep  + 
            self.brp['ccf-to-downsampled-prefix'] + 
            Path(os.path.basename(
                            self.ccfp['ccf-annotation-path'])).stem +
            '.' + 
            self.brp['ccf-to-downsampled-save-image-type'] )
        
        
        self.ccf_template_path_ds_fs = Path( 
            str(self.ds_fs_dir) + 
            os.path.sep  + 
            self.brp['downsampled-to-fullstack-prefix'] + 
            self.brp['ccf-to-downsampled-prefix'] + 
            Path(os.path.basename(
                            self.ccfp['ccf-template-path'])).stem +
            '.' + 
            self.brp['downsampled-to-fullstack-save-image-type'] )
        
        self.ccf_annotation_path_ds_fs = Path( 
            str(self.ds_fs_dir) + 
            os.path.sep  + 
            self.brp['downsampled-to-fullstack-prefix'] + 
            self.brp['ccf-to-downsampled-prefix'] + 
            Path(os.path.basename(
                            self.ccfp['ccf-annotation-path'])).stem +
            '.' + 
            self.brp['downsampled-to-fullstack-save-image-type'] )
        
        
        # can load the sample to ccf and ccf to sample scale factors now
        self.s2c, self.c2s = self.get_sample_ccf_scale_factors()
        
        # ALSO set all image instance variables to Nonw
        self.ccf_template_img = None
        self.ccf_template_ds_img = None
        self.ccf_template_img_filt = None
        self.ccf_template_ds_fs_img = None
        
        self.ccf_annotation_img = None
        self.ccf_annotation_ds_img = None
        self.ccf_annotation_ds_fs_img = None
        
    
    
    
    def create_output_dirs(self):
        '''
        Create output directories
        
        For storing output files!

        Returns
        -------
        None.

        '''
        
        print('  create output dirs..')
        
        if self.fs_ds_dir.exists() == False:
            self.fs_ds_dir.mkdir(parents = True, exist_ok=True)
            print('    made fs-to-ds dir  : '+ self.get_relative_path(self.fs_ds_dir) )
        
        if self.ds_ccf_dir.exists() == False:
            self.ds_ccf_dir.mkdir(parents = True, exist_ok=True)
            print('    made ds-to-ccf dir : '+ self.get_relative_path(self.ds_ccf_dir) )
        
        if self.ccf_ds_dir.exists() == False:
            self.ccf_ds_dir.mkdir(parents = True, exist_ok=True)
            print('    made ccf-to-ds dir : '+ self.get_relative_path(self.ccf_ds_dir) )
        
        if self.ds_fs_dir.exists() == False:
            self.ds_fs_dir.mkdir(parents = True, exist_ok=True)
            print('    made ds-to-fs dir  : '+ self.get_relative_path(self.ds_fs_dir) )
        
    
    
    
    def get_relative_path(self, path):
        """
        Returns the relative path from current working directory to path.

        Parameters
        ----------
        path : str or Path
            Path to compute relative path to.

        Returns
        -------
        str
            The relative path as a string.

        """
        path = path.resolve()
        return os.path.relpath(path, start=self.wd)
        
    
    
    def register_transform_fullstack_to_downsampled(self):
        """
        Register & Transform the fullstack to downsampled image spaces
        
        Generates the affine scaling transform from fs -> ds, and its reverse to
        move the fullstack image into downsampled space, and vice versa.  The
        downsampled resolution matches that of the CCF passed to BrainRegister,
        for built-in Allen Mouse Brain CCF this is 25µm XYZ.
        
        The fullstack image is filtered, scaled, and saved as dictated by the 
        brainregister parameters yaml, and a reference to this image is stored
        in an instance variable `template_ds_img` for further registrations.
        
        Further images at fullstack resolution are transformed to the downsampled
        image space as dictated by the brainregister parameters yaml.

        Returns
        -------
        None.

        """
        
        print('')
        print('')
        print('========================')
        print('FULLSTACK TO DOWNSAMPLED')
        print('========================')
        print('')
        
        # load template img if needed
        if (self.fs_ds_pm_path_exists() == False or 
            self.ds_fs_pm_path_exists() == False or 
            self.template_path_ds.exists() == False):
            print('  loading sample template image : ', 
                  self.get_relative_path(self.template_path) )
            self.template_img = sitk.ReadImage( str(self.template_path) )
            print('')
        
        # generate scaling param files as needed
        self.generate_scaling_param_files_fs_ds()
        
        # transform and save template ds image as needed
        self.template_ds_img = self.get_template_ds()
        self.save_template_ds()
        
        # also transform and save other sample images - if requested in the params file
        self.transform_save_fs_ds_images()
        
        # DISCARD the template_img - as this can be a large file, best to discard!
        self.template_img = None
        # discard from memory all images/martices not needed - just point vars to blank list!
        garbage = gc.collect() # run garbage collection to ensure memory is freed
        
        
    
    
    
    def fs_ds_pm_path_exists(self):
        return self.fs_ds_pm_path[0].exists()
    
    
    def ds_fs_pm_path_exists(self):
        return self.ds_fs_pm_path[0].exists()
    
    
    def save_template_ds(self):
        # save the fullstack -> downsampled sample template - if requested in params file!
        if self.brp['fullstack-to-downsampled-save-template'] == True:
            if self.template_ds_img != None:
                print('  saving downsampled template image : ' +
                  self.get_relative_path(self.template_path_ds ) )
                self.save_image(self.template_ds_img, self.template_path_ds)
            else:
                print('  template image in ds space does not exist - run get_template_ds()')

    
    
    
    def get_template_ds(self):
        
        if self.template_path_ds.exists() == False: # only transform if hte output does not exist
            
            if self.template_ds_img == None: # and if the output image is not already loaded!
                # TRANSFORM : will transform sample template to ds space
                
                if self.template_img == None:
                    print('  loading sample template image : ', 
                      self.get_relative_path(self.template_path) )
                    self.template_img = sitk.ReadImage( str(self.template_path) )
                    self.template_img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
                
                
                if self.fs_ds_pm == None:
                    print('  loading fullstack-to-downsampled transform parameters file : ' +
                          self.get_relative_path(self.fs_ds_pm_path[0] ) )
                    self.fs_ds_pm = self.load_pm_files(self.fs_ds_pm_path)
                    if self.fs_ds_pm == None:
                        print("ERROR : fs_ds_pm files do not exist - run register() first")
                
                
                # apply adaptive filter - if requested in brp
                if self.brp['fullstack-to-downsampled-adaptive-filter'] == True:
                    print('  running fullstack to downsampled adaptive filter..')
                    self.fs_ds_filter_pipeline = self.compute_adaptive_filter_fs_ds()
                    self.template_img = self.apply_adaptive_filter(
                                       self.template_img, self.fs_ds_filter_pipeline)
                
                # transform all input images with transformix
                print('  transforming sample template image..')
                print('    image : ' + 
                        self.get_relative_path(self.template_path) )
                print('    fullstack-to-downsampled elastix pm file : ' + 
                        self.get_relative_path(self.fs_ds_pm_path[0] ) )
                print('')
                print('========================================================================')
                print('')
                print('')
                self.template_ds_img = self.transform_image(self.template_img, self.fs_ds_pm)
                return self.template_ds_img
                
            else:
                print('  downsampled sample template image exists : returning image' )
                return self.template_ds_img
        
        else:
            print('  loading downsampled sample template image : ' +
                      self.get_relative_path(self.template_path_ds ) )
            self.template_ds_img = self.load_image(self.template_path_ds)
            self.template_ds_img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
            return self.template_ds_img
            
        
    
    
    def generate_scaling_param_files_fs_ds(self):
        
        if self.fs_ds_pm_path_exists() == False:
            print('  defining fullstack to downsampled scaling parameters..')
            self.fs_ds_pm = self.get_fs_ds_scaling()
            print('  saving fullstack-to-downsampled transform parameters file : ' +
                      self.get_relative_path(self.fs_ds_pm_path[0] ) )
            self.save_fs_ds_tp_file()
        else:
            print('  loading fullstack-to-downsampled transform parameters file : ' +
                      self.get_relative_path(self.fs_ds_pm_path[0] ) )
            self.fs_ds_pm = self.load_pm_files(self.fs_ds_pm_path)
        
        
        if self.ds_fs_pm_path_exists() == False:
            print('  defining downsampled to fullstack scaling parameters..')
            self.ds_fs_pm = self.get_ds_fs_scaling()
            print('  saving downsampled-to-fullstack transform parameters file : ' +
                      self.get_relative_path(self.ds_fs_pm_path[0] ) )
            self.save_ds_fs_tp_file()
        else:
            print('  loading downsampled-to-fullstack transform parameters file : ' +
                      self.get_relative_path(self.ds_fs_pm_path[0] ) )
            self.ds_fs_pm = self.load_pm_files(self.ds_fs_pm_path)
        
        print('')
        
        
    
    
    
    def  get_sample_ccf_scale_factors(self):
        
        # round to 6 dp - used by elastix!
        s2c = {key: round( 
            self.brp['sample-template-resolution'][key] / 
            self.ccfp['ccf-template-resolution'].get(key, 0), 6 )
                            for key in self.brp['sample-template-resolution'].keys()}
        
        # scale-factors in XYZ ccf -> sample
          # round to 6 dp - used by elastix!
        c2s = {key: round(
            self.ccfp['ccf-template-resolution'][key] / 
            self.brp['sample-template-resolution'].get(key, 0), 6 )
                            for key in self.ccfp['ccf-template-resolution'].keys()}
        
        #scale_matrix = np.zeros((4, 4))
        #scale_matrix[0,0] = s2c['x-um']
        #scale_matrix[1,1] = s2c['y-um']
        #scale_matrix[2,2] = s2c['z-um']
        #scale_matrix[3,3] = 1 # to set the homogenous coordinate!
        
        #at = sitk.AffineTransform(3)
         # this works because translation is (0,0,0) - so can use the LAST ROW!
        #at.SetParameters( tuple( np.reshape(scale_matrix[0:4,0:3], (1,12))[0] ) )
        
        return s2c, c2s
        
    
    
    def compute_adaptive_filter_fs_ds(self):
        
        return ImageFilterPipeline(
            str("M,"+
            str(round( (self.c2s['x-um']) / 2)) + ',' +
            str(round( (self.c2s['y-um']) / 2)) + ',' +
            str(round( (self.c2s['z-um']) / 2)) )  )

        
    
    
    def apply_adaptive_filter_fs_ds(self, img):
        
        
        if self.brp['fullstack-to-downsampled-adaptive-filter'] == True:
            
            if self.fs_ds_filter_pipeline is not None:
                
                self.fs_ds_filter_pipeline.set_image(img)
                img = self.fs_ds_filter_pipeline.execute_pipeline()
                self.fs_ds_filter_pipeline.dereference_image() # remove ref to raw data
                
                return self.fs_ds_filter_pipeline.get_filtered_image()
            
            else:
                return img
        else:
            return img
        
    
    
    
    def get_fs_ds_scaling(self):
        # , sample_template_img, c2s, s2c, brp
        # self.template_img, self.c2s, self.s2c, self.brp
        fs_ds_pm = sitk.ReadParameterFile(
                    os.path.join(BRAINREGISTER_MODULE_DIR, 'resources',
                                      'transformix-parameter-files', 
                                      '00_scaling.txt') )
        # see keys with list(fs_ds_pm)
        # see contents of keys with fs_ds_pm['key']
        
        # edit TransformParameters to correct tuple
         # use c2s - as the registration is FROM fixed TO moving!!!
        fs_ds_pm['TransformParameters'] = tuple( 
            [str("{:.6f}".format(self.c2s['x-um'])), 
             '0.000000', '0.000000','0.000000', 
             str("{:.6f}".format(self.c2s['y-um'])), 
             '0.000000','0.000000','0.000000', 
             str("{:.6f}".format(self.c2s['z-um'])), 
             '0.000000','0.000000','0.000000'] )
        
        # AND edit the Size to correct tuple
         # here want to use s2c - as this defines the size of the final FIXED image!
        fs_ds_pm['Size'] = tuple( 
            [str("{:.6f}".format( round(self.template_img.GetWidth() * self.s2c['x-um']))), 
             str("{:.6f}".format( round(self.template_img.GetHeight() * self.s2c['y-um']))),
             str("{:.6f}".format( round(self.template_img.GetDepth() * self.s2c['z-um']))) ] )
        
        # set the output format
        fs_ds_pm['ResultImageFormat'] = tuple( [ self.brp['fullstack-to-downsampled-save-image-type'] ] )
        
        fs_ds_pm = [fs_ds_pm]
        # wrap in list so this works with transform_image like any other set pof parameter maps!
        
        return fs_ds_pm
        
    
    
    
    def get_ds_fs_scaling(self):
        
        ds_fs_pm = sitk.ReadParameterFile(
                    os.path.join(BRAINREGISTER_MODULE_DIR, 'resources',
                                      'transformix-parameter-files', 
                                      '00_scaling.txt') )
        # see keys with list(ds_fs_pm)
        # see contents of keys with ds_fs_pm['key']
        
        # edit TransformParameters to correct tuple
         # use s2c - as the registration is FROM fixed TO moving!!!
        ds_fs_pm['TransformParameters'] = tuple( 
            [str("{:.6f}".format(self.s2c['x-um'])), 
             '0.000000', '0.000000','0.000000', 
             str("{:.6f}".format(self.s2c['y-um'])), 
             '0.000000','0.000000','0.000000', 
             str("{:.6f}".format(self.s2c['z-um'])), 
             '0.000000','0.000000','0.000000'] )
        
        # AND edit the Size to correct tuple
         # here want to use s2c - as this defines the size of the final FIXED image!
        ds_fs_pm['Size'] = tuple( 
            [str("{:.6f}".format( round( self.template_img.GetWidth() ))), 
             str("{:.6f}".format( round( self.template_img.GetHeight() ))),
             str("{:.6f}".format( round( self.template_img.GetDepth() ))) ] )
        
        # set the output format
        ds_fs_pm['ResultImageFormat'] = tuple( [ self.brp['downsampled-to-fullstack-save-image-type'] ] )
        
        ds_fs_pm = [ds_fs_pm]
        # wrap in list so this works with transform_image like any other set pof parameter maps!
        
        return ds_fs_pm
        
    
    
    
    def save_image(self, image, path):
        
        # save with simpleITK - much FASTER even for nrrd images!
        sitk.WriteImage(
            image,   # sitk image
            str(path), # dir plus file name
            True # useCompression set to TRUE
            )
        
        
    
    
    def load_image(self, path):
        return sitk.ReadImage(str(path))
        
    
    
    def load_transform_image_fs_ds(self, image_path):
        
        sample_img = sitk.ReadImage( str(image_path) )
        sample_img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
        
        if self.brp['fullstack-to-downsampled-adaptive-filter'] == True:
            print('    running fullstack-to-downsampled adaptive filter..')
            self.fs_ds_filter_pipeline = self.compute_adaptive_filter_fs_ds()
            sample_img = self.apply_adaptive_filter(
                                sample_img, self.fs_ds_filter_pipeline)
        
        # transform with transformix
        print('    transforming sample image..')
        print('      image : ' 
                + self.get_relative_path(image_path) )
        print('      fullstack-to-downsampled elastix pm file : ' + 
                self.get_relative_path(self.fs_ds_pm_path[0] ) )
        print('')
        print('========================================================================')
        print('')
        print('')
        sample_ds = self.transform_image(sample_img, self.fs_ds_pm)
        
        return sample_ds
        
    
    
    
    def transform_image(self, template_img, pm_list):
        
        transformixImageFilter = sitk.TransformixImageFilter()
        
        # add the first PM with Set
        transformixImageFilter.SetTransformParameterMap(pm_list[0])
        if len(pm_list) > 1: # then any subsequent ones with Add
            for i in range(1,len(pm_list)):
                transformixImageFilter.AddTransformParameterMap(pm_list[i])
        
        transformixImageFilter.SetMovingImage(template_img)
        
        transformixImageFilter.Execute()
        
        img = transformixImageFilter.GetResultImage()
        img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
        
        
        print('')
        print('========================================================================')
        print('')
        print('')
        
        # cast to the original image bitdepth
        # output is 32-bit float - convert this to the ORIGINAL image type!
        img = self.cast_image(template_img, img)
        
        
        return img
        
    
    
    def cast_image(self, sample_template_img, sample_template_ds):

        # get the minimum and maximum values in sample_template_img
        minMax = sitk.MinimumMaximumImageFilter()
        minMax.Execute(sample_template_img)
        
        # cast with numpy - as sitk casting has weird rounding errors..?
        sample_template_ds_np = sitk.GetArrayFromImage(sample_template_ds)
        
        # first rescale the pixel values to those in the original matrix
        # THIS IS NEEDED as sometimes the rescaling produces values above or below
        # the ORIGINAL IMAGE - clearly this is an error, so just crop the pixel values
        # check the number of pixels below the Minimum for example:
        #np.count_nonzero(sample_template_ds_np < minMax.GetMinimum())
        
        sample_template_ds_np[ 
            sample_template_ds_np < 
            minMax.GetMinimum() ] = minMax.GetMinimum()
        
        sample_template_ds_np[ 
            sample_template_ds_np > 
            minMax.GetMaximum() ] = minMax.GetMaximum()
        
        # NO NEED TO CAST NOW - this can be incorrect as if one pixel is aberrantly set below
        # 0 by a long way by registration quirks, this permeates into this casting, 
        # where the 0 pixels are artifically pushed up
        #sample_template_ds_cast = np.interp(
        #    sample_template_ds_np, 
        #    ( sample_template_ds_np.min(), sample_template_ds_np.max() ), 
        #    ( minMax.GetMinimum(), minMax.GetMaximum() ) 
        #        )
        
        # then CONVERT matrix to correct datatype
        if sample_template_img.GetPixelIDTypeAsString() == '16-bit signed integer':
            sample_template_ds_np = sample_template_ds_np.astype('int16')
            
        elif sample_template_img.GetPixelIDTypeAsString() == '8-bit signed integer':
            sample_template_ds_np = sample_template_ds_np.astype('int8')
            
        elif sample_template_img.GetPixelIDTypeAsString() == '8-bit unsigned integer':
            sample_template_ds_np = sample_template_ds_np.astype('uint8')
            
        elif sample_template_img.GetPixelIDTypeAsString() == '16-bit unsigned integer':
            sample_template_ds_np = sample_template_ds_np.astype('uint16')
            
        else: # default cast to unsigned 16-bit
            sample_template_ds_np = sample_template_ds_np.astype('uint16')
        
        # discard the np array
        #sample_template_ds_np = None
        
        img = sitk.GetImageFromArray( sample_template_ds_np )
        img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
        return img
        

    
    
    def save_fs_ds_tp_file(self):
        
        if self.fs_ds_pm_path[0].exists() == False:
            sitk.WriteParameterFile(self.fs_ds_pm[0], str(self.fs_ds_pm_path[0]) )
        
    
    def load_fs_ds_tp_file(self):
        """
        Load fullstack to downsampled parameter map file

        Returns
        -------
        list
            List containing the fs_ds_pm file.

        """
        
        if self.fs_ds_pm_path_exists() == True:
            return [ sitk.ReadParameterFile( str(self.fs_ds_pm_path[0]) ) ]
        else:
            return None
    
    
    
    def save_ds_fs_tp_file(self):
        
        if self.ds_fs_pm_path[0].exists() == False:
            sitk.WriteParameterFile(self.ds_fs_pm[0], str(self.ds_fs_pm_path[0]) )
        
    
    
    def load_ds_fs_tp_file(self):
        """
        Load downsampled to fullstack parameter map file

        Returns
        -------
        list
            List containing the ds_fs_pm file.
        """
        
        if self.ds_fs_pm_path_exists() == True:
            return [sitk.ReadParameterFile( str(self.ds_fs_pm_path[0]) ) ]
        else:
            return None
        
    
    
    
    def transform_save_fs_ds_images(self ):
        
        if self.brp['fullstack-to-downsampled-save-images'] == True:
            # now transform and save each sample image
            print('')
            print('  transforming and saving fs images to ds..')
            
            for i, s in enumerate(self.sample_images):
                
                self.process_image_ds(i)
                
        else:
            print('')
            print('  transforming and saving fs images to ds : not requested')
            print('')
            
        
        
    
    
    
    def process_image_ds(self, index):
        
        if self.sample_images_ds[index].exists() == False:
            
            print('')
            print('    loading sample template image : ' 
                   + self.get_relative_path(self.sample_images[index]) )
            sample_ds = self.load_transform_image_fs_ds(self.sample_images[index])
            
            self.save_image_ds(index, sample_ds)
            
        else:
            print('    downsampled image exists : ' 
                   + self.get_relative_path( self.sample_images_ds[index]) )
        
        
    
    
    def get_image_ds(self, index):
        
        if self.sample_images_ds[index].exists() == False:
            
            print('')
            print('    loading sample template image : ' 
                   + self.get_relative_path(self.sample_images[index]) )
            return self.load_transform_image_fs_ds(self.sample_images[index])
            
        else:
            print('    downsampled image exists : loading image' )
            img = sitk.ReadImage( str(self.sample_images_ds[index]))
            img.SetSpacing( tuple([1.0, 1.0, 1.0]))
            return img
        
    
    
    def save_image_ds(self, index,sample_ds):
        
        if self.sample_images_ds[index].exists() == False:
            print('    saving downsampled image : ' 
               + self.get_relative_path(self.sample_images_ds[index]) )
            self.save_image(sample_ds, self.sample_images_ds[index])
        
    
    
    
    def register_downsampled_to_ccf(self):
        
        print('')
        print('')
        print('==================')
        print('DOWNSAMPLED TO CCF')
        print('==================')
        print('')
        
        
        if self.ds_ccf_pm_files_exist() is False:
            # if the param files do not exist, generate them by registering
            # ds to ccf template
            
            if self.template_ds_img == None:
                
                if self.template_path_ds.exists() == True:
                    print('  loading ds template image : ', self.template_path_ds.name)
                    self.template_ds_img = sitk.ReadImage( str(self.template_path_ds) )
                    self.template_ds_img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
                else:
                    print('  template_ds image does not exist - generating from fs template')
                    self.template_ds_img = self.get_template_ds()
            
            
            if self.ccf_template_img == None:
                print('  loading ccf template image : ', self.ccf_template_path.name)
                # downsampled image is already loaded : sample_template_ds
                self.ccf_template_img = sitk.ReadImage( str(self.ccf_template_path) )
                self.ccf_template_img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
            
            
            # apply adaptive filter - if requested in brp
            if (self.brp['downsampled-to-ccf-prefilter'] != "none" and
                 self.ds_ccf_prefiltered == False):
                
                self.ds_ccf_prefilter()
                
            
            if self.ds_ccf_prefiltered == False:
                # REGISTRATION - use unfiltered images
                print('  registering downsampled to ccf..')
                print('    image : ' + 
                            self.get_relative_path(self.template_path_ds) )
                print('')
                print('========================================================================')
                print('')
                print('')
                self.sample_template_ds_ccf_img = self.register_image(
                                                    self.template_ds_img, 
                                                    self.ccf_template_img, 
                                                    self.ds_ccf_ep )
                
            elif self.ds_ccf_prefiltered == True:
                # REGISTRATION - use filt images
                print('  registering downsampled to ccf after prefilter..')
                print('    image : ' + 
                            self.get_relative_path(self.template_path_ds) )
                print('')
                print('========================================================================')
                print('')
                print('')
                
                self.sample_template_ds_ccf_img = self.register_image(
                                                    self.template_ds_img_filt, 
                                                    self.ccf_template_img_filt, 
                                                    self.ds_ccf_ep )
            
            print('  saving downsampled to ccf parameter map file[s]..')
            self.save_pm_files( self.ds_ccf_pm_paths )
            
        else:
            print('  downsampled to ccf parameter map file[s] already exist : No Registration')
        
        
    
    
    
    def register_ccf_to_downsampled(self):
        
        print('')
        print('')
        print('==================')
        print('CCF TO DOWNSAMPLED')
        print('==================')
        print('')
        
        
        if self.ccf_ds_pm_files_exist() is False: # if the param files do not exist
            # generate them by registering ccf to ds template
            
            if self.template_ds_img == None:
                
                if self.template_path_ds.exists() == True:
                    print('  loading ds template image : ', self.template_path_ds.name)
                    self.template_ds_img = sitk.ReadImage( str(self.template_path_ds) )
                    self.template_ds_img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
                else:
                    print('  template_ds image does not exist - generating from fs template')
                    self.template_ds_img = self.get_template_ds()
            
            
            if self.ccf_template_img == None:
                print('  loading ccf template image : ', self.ccf_template_path.name)
                # downsampled image is already loaded : sample_template_ds
                self.ccf_template_img = sitk.ReadImage( str(self.ccf_template_path) )
                self.ccf_template_img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
            
            
            # apply adaptive filter - if requested in brp
            if (self.brp['ccf-to-downsampled-prefilter'] != "none" and
                 self.ccf_ds_prefiltered == False):
                
                self.ccf_ds_prefilter()
                
            
            
            if self.ccf_ds_prefiltered == False:
                # REGISTRATION
                print('  registering ccf to downsampled..')
                print('    image : ' + 
                            self.get_relative_path(self.template_path_ds) )
                print('')
                print('========================================================================')
                print('')
                print('')
                
                self.sample_template_ccf_ds_img = self.register_image(
                                                    self.ccf_template_img, 
                                                    self.template_ds_img, 
                                                    self.ccf_ds_ep )
                
            elif self.ccf_ds_prefiltered == True:
                # REGISTRATION - use filt images
                print('  registering ccf to downsampled after prefilter..')
                print('    image : ' + 
                            self.get_relative_path(self.template_path_ds) )
                print('')
                print('========================================================================')
                print('')
                print('')
                
                self.sample_template_ccf_ds_img = self.register_image( 
                                                    self.ccf_template_img_filt, 
                                                    self.template_ds_img_filt, 
                                                    self.ccf_ds_ep )
            
            print('  saving ccf to downsampled parameter map file[s]..')
            self.save_pm_files( self.ccf_ds_pm_paths )
            
        else:
            print('  ccf to downsampled parameter map file[s] already exist : No Registration')
        
    
    
    
    def ds_ccf_prefilter(self):
        
        print('  running downsampled to ccf prefilter..')
        self.ds_ccf_filter_pipeline = self.compute_adaptive_filter(
            self.brp['downsampled-to-ccf-prefilter'] )
        
        print('    ds template')
        self.template_ds_img_filt = self.apply_adaptive_filter(
                                self.template_ds_img, 
                                self.ds_ccf_filter_pipeline )
        
        print('    ccf template')
        self.ccf_template_img_filt = self.apply_adaptive_filter(
                                    self.ccf_template_img, 
                                    self.ds_ccf_filter_pipeline )
        
        self.ds_ccf_prefiltered = True # set to True to check if prefiltered later
        self.ccf_ds_prefiltered = False
    
    
    
    def ccf_ds_prefilter(self):
        
        print('  running ccf to downsampled prefilter..')
        self.ccf_ds_filter_pipeline = self.compute_adaptive_filter(
            self.brp['ccf-to-downsampled-prefilter'] )
        
        print('    ds template')
        self.template_ds_img_filt = self.apply_adaptive_filter(
                                self.template_ds_img, 
                                self.ccf_ds_filter_pipeline )
        
        print('    ccf template')
        self.ccf_template_img_filt = self.apply_adaptive_filter(
                                    self.ccf_template_img, 
                                    self.ccf_ds_filter_pipeline )
        
        self.ds_ccf_prefiltered = False
        self.ccf_ds_prefiltered = True # set to True to check if prefiltered later
    
    
    
    def get_elastix_params(self, param_files):
        """
        Returns the elastix parameter map files as VectorOfParameterMap Object
        
        

        Returns
        -------
        parameterMapVector : VectorOfParameterMap
            Vector of Parameter Map files for use with elastix.

        """
        
        parameterMapVector = sitk.VectorOfParameterMap()
        
        for pf in param_files:
            
            if pf == 'brainregister_affine':
                pm = sitk.ReadParameterFile(
                         os.path.join(BRAINREGISTER_MODULE_DIR, 'resources', 
                                 'elastix-parameter-files', '01_affine.txt') )
                
            elif pf == 'brainregister_bspline':
                pm = sitk.ReadParameterFile(
                         os.path.join(BRAINREGISTER_MODULE_DIR, 'resources', 
                                 'elastix-parameter-files', '02_bspline.txt') )
                
            else: # open relative file specified in pf
                pm = sitk.ReadParameterFile( 
                      str(Path(os.path.join(str(self.brp_dir), pf)).resolve())
                )
            
            parameterMapVector.append(pm)
            
            
        return parameterMapVector
        
    
    
    def register_image(self, moving_img, fixed_img, parameter_map_vector):
        
        # perform elastix registration
        elastixImageFilter = sitk.ElastixImageFilter()
        
        elastixImageFilter.SetMovingImage(moving_img)
        elastixImageFilter.SetFixedImage(fixed_img)
        
        elastixImageFilter.SetParameterMap(parameter_map_vector)
        
        elastixImageFilter.Execute()
        
        # remove the registration logs
        reg_logs = [f for f in os.listdir('.') if 
                    os.path.isfile(f) & 
                    os.path.basename(f).startswith("IterationInfo.")]
        for rl in reg_logs:
            os.remove(rl)
            
        
        print('')
        print('========================================================================')
        print('')
        print('')
        
        # get the registered image
        img = elastixImageFilter.GetResultImage()
        img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
        return img
    
    
    
    def save_pm_files(self, pm_paths):
        
        # move TransformParameters files to downsampled-to-ccf directory
        transform_params = [f for f in os.listdir('.') if os.path.isfile(f) & 
                            os.path.basename(f).startswith("TransformParameters.")]
        
        transform_params.sort() # into ASCENDING ORDER
        
        for i, tp in enumerate(transform_params):
            os.rename(tp, str(pm_paths[i]) )
        
        
    
    
    def load_pm_files(self, pm_paths ):
        
        if pm_paths[0].exists() == True: # assume if first pm file exists they all do!
            pms = []
            for pm in pm_paths:
                pms.append(sitk.ReadParameterFile( str(pm) ) )
            
            return pms
        else:
            return None # if doesnt exist return none - mainly for call in resolve_params()
        
    
    
    def ds_ccf_pm_files_exist(self):
        """
        Returns true only if all ds_ccf_pm files exist

        Returns
        -------
        None.

        """
        
        exists = True
        for pm in self.ds_ccf_pm_paths:
            if pm.exists() is False:
                exists = False
        
        return exists
        
    
    
    def ccf_ds_pm_files_exist(self):
        """
        Returns true only if all ccf_ds_pm files exist

        Returns
        -------
        None.

        """
        
        exists = True
        for pm in self.ccf_ds_pm_paths:
            if pm.exists() is False:
                exists = False
        
        return exists
        
    
    
    def compute_adaptive_filter(self, filter_string):
        
        if filter_string == 'adaptive':
            return ImageFilterPipeline('M,4,4,4')
            # TODO figure out how to COMPUTE an adaptive filter here!
            #self.sample_template_ds_img, 
            #self.ccf_template_img
            
        elif filter_string == 'none':
            return None
            
        else:
            # TODO syntax for user defining their own filter?
            # Writing in new Class ImageFilterPipeline
            return ImageFilterPipeline(filter_string)
        
    
    
    
    def apply_adaptive_filter(self, img, filter_pipeline):
        
        if filter_pipeline is not None:
            
            filter_pipeline.set_image(img)
            img = filter_pipeline.execute_pipeline()
            filter_pipeline.dereference_image() # remove ref to raw data
            
            return filter_pipeline.get_filtered_image()
        
        else:
            return img
    
    
    
    
    def transform_downsampled_to_ccf(self):
    
        if self.brp['downsampled-to-ccf-save-template'] == True:
            
            # TRANSFORM : will transform sample template ds to ccf space
            self.template_ds_ccf_img = self.get_ds_template_ccf()
            self.save_ds_template_ccf()
        
        else:
            # downsampled to ccf template is not to be saved - pass
            print('')
            print('  transforming and saving ds template image to ccf : not requested')
            print('')
        
        
        if self.brp['downsampled-to-ccf-save-images'] == True:
            
            for i,im_ds in enumerate(self.sample_images_ds):
                
                # TRANSFORM : will transform sample template ds to ccf space
                image = self.get_ds_image_ccf(i)
                
                self.save_ds_image_ccf(i, image)
                
            
        else:
            # downsampled to ccf of sample img is not to be saved - pass
            print('')
            print('  transforming and saving ds images to ccf : not requested')
            print('')
            
        
        # discard from memory all images/martices not needed - just point vars to blank list!
        garbage = gc.collect() # run garbage collection to ensure memory is freed
        
        
    
    
    
    def save_ds_template_ccf(self):
        
        if self.template_path_ds_ccf.exists() == False:
            if self.template_ds_ccf_img != None:
                print('  saving ds template image to ccf : ' +
                  self.get_relative_path(self.template_path_ds ) )
                self.save_image(self.template_ds_ccf_img, self.template_path_ds_ccf)
            else:
                print('  ds template image in ccf space does not exist - run get_ds_template_ccf()')
    
    
    
    def get_ds_template_ccf(self):
        
        if self.template_path_ds_ccf.exists() == False: # only transform if output does not exist
            
            if self.template_ds_ccf_img == None: # and if the output image is not already loaded!
                
                if self.template_path_ds.exists() == False:
                    print('template ds does not exist - transforming from fs..')
                    # create template_ds_img by transforming from the fs template image
                    self.template_ds_img = self.load_transform_image_fs_ds(self.template_path)
                
                elif self.template_ds_img is None:
                    print('template ds image not loaded - loading image..')
                    self.template_ds_img = sitk.ReadImage( str(self.template_path_ds))
                    self.template_ds_img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
                
                
                if self.ds_ccf_pm is None:
                    print('  ds to ccf paramater maps not loaded - loading files..')
                    self.ds_ccf_pm = self.load_pm_files( self.ds_ccf_pm_paths )
                
                print('  transforming sample template ds image..')
                print('    image : ' + 
                        self.get_relative_path(self.template_path_ds) )
                
                for i, pm in enumerate(self.ds_ccf_pm_paths):
                    print('    downsampled-to-ccf paramter map file '+
                            str(i) + ' : ' + 
                            self.get_relative_path(pm) )
                
                print('========================================================================')
                print('')
                print('')
                return self.transform_image(self.template_ds_img, self.ds_ccf_pm )
            
            else:
                print('  ds template to ccf space exists - returning image..')
                return self.template_ds_ccf_img
        
        else:
            print('  ds template to ccf space exists - loading image..')
            return self.load_image(self.template_path_ds_ccf)
        
        
    
    
    
    def save_ds_image_ccf(self, index, image):
        
        if self.sample_images_ds_ccf[index].exists() == False: # only transform if output does not exist
            print('  saving downsampled to ccf image : ' +
                  self.get_relative_path(self.sample_images_ds_ccf[index] ) )
            self.save_image(image, self.sample_images_ds_ccf[index])
            
    
    
    
    def get_ds_image_ccf(self, index):
        
        im_ds = self.sample_images_ds[index]
        
        if self.sample_images_ds_ccf[index].exists() == False: # only transform if output does not exist
            
            if im_ds.exists() == False:
                # create img_ds by transforming from the fs sample image
                img_ds = self.load_transform_image_fs_ds(self.sample_images[index])
            
            else:
                # if ds sample img exists already, load it!
                img_ds = sitk.ReadImage( str(im_ds))
                img_ds.SetSpacing( tuple([1.0, 1.0, 1.0]) )
            
            
            if self.ds_ccf_pm is None:
                print('  ds to ccf paramater maps not loaded - loading files..')
                self.ds_ccf_pm = self.load_pm_files( self.ds_ccf_pm_paths )
            
            
            print('  transforming sample ds image..')
            print('    image : ' + 
                    self.get_relative_path(im_ds) )
            
            for j, pm in enumerate(self.ds_ccf_pm_paths):
                print('    downsampled-to-ccf paramter map file '+
                        str(j) + ' : ' + 
                        self.get_relative_path(pm) )
            print('========================================================================')
            print('')
            print('')
            
            img_ds_ccf = self.transform_image(img_ds, self.ds_ccf_pm)
            img_ds_ccf.SetSpacing( tuple([1.0, 1.0, 1.0]) )
            return img_ds_ccf
        
        else:
            print('  ds image to ccf space exists - loading image.. ' +
                      self.get_relative_path(im_ds))
            img_ds_ccf =  sitk.ReadImage( str(self.sample_images_ds_ccf[index]))
            img_ds_ccf.SetSpacing( tuple([1.0, 1.0, 1.0]) )
            return img_ds_ccf
        
        
    
    
    
    
    def transform_ccf_to_downsampled(self):
        
        
        if self.brp['ccf-to-downsampled-save-template'] == True:
            
            # TRANSFORM : will transform sample template ds to ccf space
            self.ccf_template_ds_img = self.get_ccf_template_ds()
            
            self.save_ccf_template_ds()
        
        else:
            # downsampled to ccf template is not to be saved - pass
            print('')
            print('  transforming and saving ccf template image to ds : not requested')
            print('')
        
        
        if self.brp['ccf-to-downsampled-save-annotation'] == True:
            
            # TRANSFORM : will transform ccf annotation to ds space
            self.ccf_annotation_ds_img = self.get_ccf_annotation_ds()
            self.save_ccf_annotation_ds()
            
        
        else:
            # downsampled to ccf of sample img is not to be saved - pass
            print('')
            print('  transforming and saving ccf annotation to ds : not requested')
            print('')
            
        
        # discard from memory all images/martices not needed - just point vars to blank list!
        garbage = gc.collect() # run garbage collection to ensure memory is freed
        
    
    
    
    def save_ccf_template_ds(self):
        
        if self.ccf_template_path_ds.exists() == False: # only transform if output does not exist
            if self.ccf_template_ds_img != None:
                print('  saving ccf template image to ds : ' +
                      self.get_relative_path(self.ccf_template_path_ds ) )
                self.save_image(self.ccf_template_ds_img, self.ccf_template_path_ds)
            else:
                print('  ccf template image in ds space does not exist - run get_ccf_template_ds()')
    
    
    
    def get_ccf_template_ds(self):
        
        if self.ccf_template_path_ds.exists() == False: # only transform if output does not exist on disk
            
            if self.ccf_template_ds_img == None: # and if the output image is not already loaded!
                
                if self.ccf_template_img is None:
                    print('  ccf template image not loaded - loading image..')
                    self.ccf_template_img = sitk.ReadImage( str(self.ccf_template_path))
                    self.ccf_template_img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
                
                
                if self.ccf_ds_pm is None:
                    print('  ccf to ds paramater maps not loaded - loading files..')
                    self.ccf_ds_pm = self.load_pm_files( self.ccf_ds_pm_paths )
                
                # transform all input images with transformix
                print('  transforming ccf template to ds space..')
                print('    image : ' + 
                        self.get_relative_path(self.ccf_template_path) )
                
                for i, pm in enumerate(self.ccf_ds_pm_paths):
                    print('    ccf-to-downsampled paramter map file '+
                            str(i) + ' : ' + 
                            self.get_relative_path(pm) )
                
                print('========================================================================')
                print('')
                print('')
                
                self.ccf_template_ds_img = self.transform_image(self.ccf_template_img, self.ccf_ds_pm )
                return self.ccf_template_ds_img
            
            else:
                print('  ccf template to ds space exists - returning image..')
                return self.ccf_template_ds_img
        
        
        else:
            print('  ccf template to ds space exists - loading image..')
            self.ccf_template_ds_img = sitk.ReadImage( str(self.ccf_template_path_ds) )
            self.ccf_template_ds_img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
            return
        
    
    
    
    def save_ccf_annotation_ds(self):
        
        if self.ccf_annotation_path_ds.exists() == False: # only transform if output does not exist
            if self.ccf_annotation_ds_img != None:
                print('  saving ccf to downsampled annotation : ' +
                      self.get_relative_path(self.ccf_annotation_path_ds ) )
                self.save_image(self.ccf_annotation_ds_img, self.ccf_annotation_path_ds )
            else:
                print('  ccf annotation image in ds space does not exist - run get_ccf_annotation_ds()')
    
    
    def get_ccf_annotation_ds(self):
        
        if self.ccf_annotation_path_ds.exists() == False: # only transform if output does not exist
            
            if self.ccf_annotation_ds_img == None: # and if the output image is not already loaded!
                
                if self.ccf_annotation_img == None:
                    self.ccf_annotation_img = sitk.ReadImage(str(self.ccf_annotation_path))
                    self.ccf_annotation_img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
                
                if self.ccf_ds_pm_anno == None:
                    # generate the ccf_ds_pm_anno from ccf_ds_pm
                    print('  ccf to ds annotation paramater maps not loaded - loading files..')
                    if self.ccf_ds_pm == None: # load ccf_ds_pm first if needed
                        self.ccf_ds_pm = self.load_pm_files( self.ccf_ds_pm_paths )
                        if self.ccf_ds_pm == None:
                            print("ERROR : ccf_ds_pm files do not exist - run register() first")
                    self.ccf_ds_pm_anno = self.edit_pms_nearest_neighbour(self.ccf_ds_pm)
                
                print('  transforming ccf annotation image..')
                print('    image : ' + 
                        self.get_relative_path(self.ccf_annotation_path) )
                
                for j, pm in enumerate(self.ccf_ds_pm_paths):
                    print('    ccf-to-downsampled paramter map file '+
                            str(j) + ' : ' + 
                            self.get_relative_path(pm) )
                print('========================================================================')
                print('')
                print('')
                
                self.ccf_annotation_ds_img = self.transform_image(self.ccf_annotation_img, self.ccf_ds_pm_anno)
                return self.ccf_annotation_ds_img
            else:
                print('  ccf annotation to ds space exists - returning image..')
                return self.ccf_annotation_ds_img
        
        else:
            print('  ccf annotation to ds space exists - loading image..')
            self.ccf_annotation_ds_img = sitk.ReadImage( str(self.ccf_annotation_path_ds) )
            self.ccf_annotation_img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
            return self.ccf_annotation_ds_img
        
        
    
    
    
    def edit_pms_nearest_neighbour(self, pms):
        
        if pms == None:
            return None # this is so initial calls in resolve_param_paths()
                        # is set to None if pm files dont exist
        else:
            # FIRST alter the pm files FinalBSplineInterpolationOrder to 0
            # 0 - nearest neighbour interpolation for annotation images
            for pm in pms:
                pm['FinalBSplineInterpolationOrder'] = tuple( [ str(0) ] )
            
            return pms
    
    
    
    
    def transform_downsampled_to_fullstack(self):
        
        print('')
        print('')
        print('========================')
        print('DOWNSAMPLED TO FULLSTACK')
        print('========================')
        print('')
        
        if self.brp['downsampled-to-fullstack-save-template'] == True:
            
            # TRANSFORM : will ccf template ds to fs space
            self.ccf_template_ds_fs_img = self.get_ccf_template_ds_fs()
            self.save_ccf_template_ds_fs()
        
        else:
            # downsampled to ccf template is not to be saved - pass
            print('')
            print('  transforming and saving ccf template ds image to fs : not requested')
            print('')
            
        
        if self.brp['downsampled-to-fullstack-save-annotation'] == True:
            
            # TRANSFORM : will transform ccf annotation to ds space
            self.ccf_annotation_ds_fs_img = self.get_ccf_annotation_ds_fs()
            self.save_ccf_annotation_ds_fs()
            
        
        else:
            # downsampled to ccf of sample img is not to be saved - pass
            print('')
            print('  transforming and saving ccf annotation ds to fs : not requested')
            print('')
            
        
        # discard from memory all images/martices not needed - just point vars to blank list!
        garbage = gc.collect() # run garbage collection to ensure memory is freed
        
    
    
    
    
    def save_ccf_template_ds_fs(self):
        
        if self.ccf_template_path_ds_fs.exists() == False: # only save if output does not exist
            print('  saving ccf template ds image to fs : ' +
                  self.get_relative_path(self.ccf_template_path_ds_ds ) )
            self.save_image(self.ccf_template_ds_fs_img, self.ccf_template_path_ds_fs)
    
    
    
    def get_ccf_template_ds_fs(self):
        
        if self.ccf_template_path_ds_fs.exists() == False: # only transform if output does not exist
            
            if self.ccf_template_ds_fs_img == None: # and if the output image is not already loaded!
            
                if self.ccf_template_ds_img is None:
                    print('  ccf template image not loaded - loading image..')
                    self.ccf_template_ds_img = self.get_ccf_template_ds()
                
                
                if self.ds_fs_pm is None:
                    print('  ccf to ds paramater maps not loaded - loading files..')
                    self.ds_fs_pm = self.load_pm_files( self.ds_fs_pm_path )
                
                # transform all input images with transformix
                print('  transforming ccf template ds to fs space..')
                print('    image : ' + 
                        self.get_relative_path(self.ccf_template_path_ds) )
                
                for i, pm in enumerate(self.ds_fs_pm_path):
                    print('    downsampled to fullstack paramter map file '+
                            str(i) + ' : ' + 
                            self.get_relative_path(pm) )
                
                print('========================================================================')
                print('')
                print('')
                
                return self.transform_image(self.ccf_template_ds_img, self.ds_fs_pm )
            
            else:
                print('  ccf template ds to fs space exists - returning image..')
                return self.ccf_template_ds_fs_img
        
        else:
            print('  ccf template ds to fs space exists - loading image..')
            self.ccf_template_ds_fs_img = sitk.ReadImage( str(self.ccf_template_path_ds_fs) )
            self.ccf_template_ds_fs_img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
            return self.ccf_template_ds_fs_img
        
    
    
    
    def save_ccf_annotation_ds_fs(self):
        
        if self.ccf_annotation_path_ds_fs.exists() == False: # only save if output does not exist
            print('  saving ds annotation to fs : ' +
                  self.get_relative_path(self.ccf_annotation_path_ds_fs ) )
            self.save_image(self.ccf_annotation_ds_fs_img, self.ccf_annotation_path_ds_fs )
    
    
    
    def get_ccf_annotation_ds_fs(self):
        
        if self.ccf_annotation_path_ds_fs.exists() == False: # only transform if output does not exist
            
            if self.ccf_annotation_ds_fs_img == None: # and if the output image is not already loaded!
                
                if self.ccf_annotation_ds_img == None:
                    self.ccf_annotation_ds_img = self.get_ccf_annotation_ds()
                
                if self.ds_fs_pm_anno == None:
                    # generate the ds_fs_pm_anno from ccf_ds_pm
                    print('  ds to fs annotation paramater maps not loaded - loading files..')
                    if self.ds_fs_pm == None: # load ccf_ds_pm first if needed
                        self.ds_fs_pm = self.load_pm_files( self.ds_fs_pm_path )
                        if self.ds_fs_pm == None:
                            print("ERROR : ds_fs_pm files do not exist - run register() first")
                    self.ds_fs_pm_anno = self.edit_pms_nearest_neighbour(self.ds_fs_pm)
                
                print('  transforming ccf annotation ds image..')
                print('    image : ' + 
                        self.get_relative_path(self.ccf_annotation_path_ds) )
                
                for j, pm in enumerate(self.ds_fs_pm_path):
                    print('    downsampled-to-fullstack paramter map file '+
                            str(j) + ' : ' + 
                            self.get_relative_path(pm) )
                print('========================================================================')
                print('')
                print('')
                
                return self.transform_image(self.ccf_annotation_ds_img, self.ds_fs_pm_anno)
            else:
                print('  ccf annotation ds to fs space exists - returning image..')
                return self.ccf_annotation_ds_fs_img
        
        else:
            print('  ccf annotation ds to fs space exists - loading image..')
            self.ccf_annotation_ds_fs_img = sitk.ReadImage( str(self.ccf_annotation_path_ds_fs) )
            self.ccf_annotation_ds_fs_img.SetSpacing( tuple([1.0, 1.0, 1.0]) )
            return self.ccf_annotation_ds_fs_img
        
        
    



class ImageFilterPipeline(object):
    
    
    def __init__(self, filter_string):
        
        self.img_filter = []
        self.img_filter_name = []
        self.img_filter_kernel = []
        # process string to determine the filter pipe
        # eg. M,1,1,0-GH,10,10,4 -> translates to 
            # median 4x4 XY THEN gaussian high-pass 10x10x4 XYZ
        filter_list = filter_string.split(sep='-')
        
        for f in filter_list:
            
            filter_code = ''.join([c for c in f if c.isupper()])
            filter_kernel = tuple([int(s) for s in f.split(',') if s.isdigit()])
            
            if filter_code == 'M':
                
                flt = sitk.MedianImageFilter()
                flt.SetRadius(filter_kernel)
                
                self.img_filter.append(flt)
                self.img_filter_name.append('Median')
                self.img_filter_kernel.append(filter_kernel)
                
            elif filter_code == 'G':
                
                flt = sitk.SmoothingRecursiveGaussianImageFilter()
                flt.SetSigma(filter_kernel)
                
                self.img_filter.append(flt)
                self.img_filter_name.append('Gaussian')
                self.img_filter_kernel.append(filter_kernel)
                
            elif filter_code == 'GH':
                
                flt = sitk.SmoothingRecursiveGaussianImageFilter()
                flt.SetSigma(filter_kernel)
                
                self.img_filter.append(flt)
                self.img_filter_name.append('Gaussian-High-Pass')
                self.img_filter_kernel.append(filter_kernel)
                
            
        
    
    
    def set_image(self, img):
        """
        Set the image
        
        MUST be of type sitk.Image

        Parameters
        ----------
        img : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        """
        
        
        self.img = img
    
    
    def get_image(self):
        return self.img
    
    def dereference_image(self):
        """
        Dereference the images  in this filter pipeline
        
        This may be required to help free memory by discarding this objects 
        reference to the raw image.

        Returns
        -------
        None.

        """
        self.img = None
    
    def get_filtered_image(self):
        return self.filtered_img
    
    
    def execute_pipeline(self):
        
        img = self.img
        
        #print('')
        #print('  Execute ImageFilterPipeline:')
        for i, f in enumerate(self.img_filter):
            #print('    Filter Type : ' + self.img_filter_name[i])
            #print('    Filter Kernel : ' + str(self.img_filter_kernel[i]) )
            img = f.Execute(img)
            
        self.filtered_img = img
        
        return self.filtered_img
    
    
    def cast_image(self):
        
        # get the minimum and maximum values in self.img
        minMax = sitk.MinimumMaximumImageFilter()
        minMax.Execute(self.img)
        
        # cast with numpy - as sitk casting has weird rounding errors..?
        filtered_img_np = sitk.GetArrayFromImage(self.filtered_img)
        
        # first rescale the pixel values to those in the original matrix
        # THIS IS NEEDED as sometimes the rescaling produces values above or below
        # the ORIGINAL IMAGE - clearly this is an error, so just crop the pixel values
        # check the number of pixels below the Minimum for example:
        #np.count_nonzero(filtered_img_np < minMax.GetMinimum())
        
        filtered_img_np[ 
            filtered_img_np < 
            minMax.GetMinimum() ] = minMax.GetMinimum()
        
        filtered_img_np[ 
            filtered_img_np > 
            minMax.GetMaximum() ] = minMax.GetMaximum()
        
        # NO NEED TO CAST - this is incorrect as if one pixel is aberrantly set below
        # 0 by a long way, this permeates into this casting, where the 0 pixels are
        # artifically pushed up
        #self.filtered_img_cast = np.interp(
        #    filtered_img_np, 
        #    ( filtered_img_np.min(), filtered_img_np.max() ), 
        #    ( minMax.GetMinimum(), minMax.GetMaximum() ) 
        #        )
        
        # then CONVERT matrix to correct datatype
        if self.img.GetPixelIDTypeAsString() == '16-bit signed integer':
            filtered_img_np = filtered_img_np.astype('int16')
            
        elif self.img.GetPixelIDTypeAsString() == '8-bit signed integer':
            filtered_img_np = filtered_img_np.astype('int8')
            
        elif self.img.GetPixelIDTypeAsString() == '8-bit unsigned integer':
            filtered_img_np = filtered_img_np.astype('uint8')
            
        elif self.img.GetPixelIDTypeAsString() == '16-bit unsigned integer':
            filtered_img_np = filtered_img_np.astype('uint16')
            
        else: # default cast to unsigned 16-bit
            filtered_img_np = filtered_img_np.astype('uint16')
        
        # discard the np array
        #filtered_img_np = None
        
        self.filtered_img = filtered_img_np
        
    
    
    


