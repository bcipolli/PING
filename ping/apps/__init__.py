"""
Accessing remote PING data & methods
"""
import hashlib
import os
import tempfile

import numpy as np
import requests


class PINGSession(object):
    """
    """
    project_name = 'PING'
    base_url = 'https://ping-dataportal.ucsd.edu/'

    def __init__(self, username=None, passwd=None, verbose=1):
        self.username = username or os.environ.get('PING_USERNAME')
        self.passwd = passwd or os.environ.get('PING_PASSWORD')

        if self.username is None:
            raise ValueError("username must be specified, or read from environment variables PING_USERNAME")
        elif '@' in self.username:
            raise ValueError('You must log in with your username, not email address, for these functions to work.')
        if self.passwd is None:
            raise ValueError("password must be specified, or read from environment variables PING_PASSWORD")

        self.sess = requests.Session()
        self.result_ids = None  # current dictionary of result IDs
        self.verbose = verbose  # level of output

    def log(self, message, verbose=1):
        if self.verbose >= verbose:
            print(message)

    def make_url(self, rel_path):
        template_url = '{base_url}{rel_path}'.format(base_url=self.base_url,
                                                     rel_path=rel_path)
        return template_url.format(project_name=self.project_name)

    def make_request(self, rel_path, verb='get', msg=None, **kwargs):
        url = self.make_url(rel_path)
        msg = msg or "Sending '%s' request to %s ..." % (verb, url)

        self.log(msg)
        request_fn = getattr(self.sess, verb)
        resp = request_fn(url, **kwargs)
        self.log("Response received.", verbose=-1)

        return resp

    def download_file(self, rel_path, out_file=None, **kwargs):
        resp = self.make_request(rel_path=rel_path, **kwargs)
        out_text = resp.text

        if out_file:
            # Make the directory and dump the file.
            dir_path = os.path.dirname(out_file)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

            with open(out_file, 'w') as fp:
                fp.write(out_text)

        return out_text

    def login(self):
        payload = {
            'username': self.username,
            'pw': hashlib.md5(self.passwd.encode()).hexdigest(),
            'ac': 'log',
            'url': ''}

        resp = self.make_request(rel_path='applications/User/login.php',
                                 verb='post', data=payload,
                                 msg="Logging in as %s" % (self.username))
        if 'Login to Data Portal' in resp.text or resp.url != self.make_url('index.php'):
            raise Exception('Login failed.')
        else:
            self.log("Logged in as %s successfully." % self.username)

    def expert_mode_script(self, X, Y, covariates=[]):
        """Produce the necessary 'expert' script"""
        return """dependent.measure     = "{Y}"
covariates.usr        = "{covariates}"
covariates.ses        = "FDH_Highest_Education + FDH_3_Household_Income"
covariates.dev        = "DeviceSerialNumber"
covariates.gaf        = "GAF_africa + GAF_amerind + GAF_eastAsia + GAF_oceania + GAF_centralAsia"
independent.variable  = "{X}"
smoothing.interaction = ""
""".format(X=X, Y=Y, covariates='+'.join(covariates))

    def regress(self, X, Y, covariates=[], **kwargs):
        """Do the regression remotely (via R), return the raw result.
        """
        cookie = np.random.randint(1000)
        payload = {
            '_v': '',
            'cookie': cookie,
            'user_name': self.username,
            'project_name': self.project_name,
            'command': '+'.join(covariates),
            'yvalue': Y,
            'functionOf': X,
            'interaction': '',
            'expert': self.expert_mode_script(X, Y, covariates)}
        payload.update(**kwargs)

        # Generate the regression and store the result.
        self.log("Computing regression for %s vs. %s..." % (X, Y))
        resp = self.make_request('applications/DataExploration/executeR.php',
                                 verb='post', data=payload)
        r_text = str(resp.text)
        return r_text

    def download_PING_spreadsheet(self, out_file=None):
        # Upload a dummy user spreadsheet, to get a 'pure' PING spreadsheet.
        fname = '%s.csv' % tempfile.mkstemp()[1]
        with open(fname, 'w') as fp:
            fp.write("")
        self.upload_user_spreadsheet(csv_file=fname)

        # Force creation of the PING spreadsheet by running a regression
        self.log("Do a simple regression to make sure PING spreadsheet is created.")
        self.regress('Age_At_IMGExam', 'MRI_cort_area.ctx.total')

        # Now access the PING data sheet
        out_text = self.download_file(
            rel_path='applications/Documents/downloadDoc.php?project_name={project_name}&version=&file=../usercache_PING_%s.csv' % (
                self.username),
            out_file=out_file)

        return out_text

    def upload_user_spreadsheet(self, csv_file):
        files = {
            'userfile': open(csv_file, 'r')}
        payload = {
            'MAX_FILE_SIZE': 20000000,
            'project': self.project_name,
            'version': ''}

        resp = self.make_request('applications/DataExploration/upload.php',
                                 verb='post', data=payload, files=files,
                                 msg="Uploading spreadsheet %s to server..." % csv_file)

        if 'upload was successful' not in resp.text:
            raise Exception('Upload failed: %s' % str(resp.text))
