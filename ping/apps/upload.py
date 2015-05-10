"""
Upload a custom spreadsheet from the command-line
"""
from ..access import PINGSession


class PINGUploadSession(PINGSession):

    def upload_user_spreadsheet(self, csv_file):
        files = {
            'userfile': open(csv_file, 'r')}
        payload = {
            'MAX_FILE_SIZE': 20000000,
            'project': 'PING',
            'version': ''}

        self.log("Uploading spreadsheet %s to server..." % csv_file)
        resp = self.sess.post('https://ping-dataportal.ucsd.edu/applications/DataExploration/upload.php',
                              data=payload, files=files)
        if 'upload was successful' not in resp.text:
            raise Exception('Upload failed: %s' % str(resp.text))
