import unittest
import os
from ...BaseTestCase import BaseTestCase
from kombi.Task import Task
from kombi.Crawler.Fs import FsCrawler
from kombi.Task.Fs.ChecksumTask import ChecksumTaskMatchError
from kombi.Task.Image import UpdateImageMetadataTask

class UpdateImageMetadataTaskTest(BaseTestCase):
    """Test UpdateImageMetadata task."""

    __sourcePath = os.path.join(BaseTestCase.dataTestsDirectory(), "test.exr")
    __targetPath = os.path.join(BaseTestCase.tempDirectory(), "testToDelete.exr")

    def testUpdateImageMetadata(self):
        """
        Test that the UpdateImageMetadata task works properly.
        """
        crawler = FsCrawler.createFromPath(self.__sourcePath)
        updateTask = Task.create('updateImageMetadata')
        updateTask.add(crawler, self.__targetPath)
        result = updateTask.output()
        self.assertEqual(len(result), 1)
        crawler = result[0]

        import OpenImageIO as oiio
        inputSpec = oiio.ImageInput.open(self.__targetPath).spec()
        self.assertEqual(inputSpec.get_string_attribute("kombi:sourceFile"), self.__sourcePath)
        checkTask = Task.create('checksum')
        checkTask.add(crawler, self.__sourcePath)
        self.assertRaises(ChecksumTaskMatchError, checkTask.output)

        customMetadata = {"testInt": 0, "testStr": "True"}
        UpdateImageMetadataTask.updateDefaultMetadata(inputSpec, crawler, customMetadata)
        self.assertEqual(inputSpec.get_int_attribute("kombi:testInt"), 0)
        self.assertEqual(inputSpec.get_string_attribute("kombi:testStr"), "True")

    @classmethod
    def tearDownClass(cls):
        """
        Remove the file that was created.
        """
        os.remove(cls.__targetPath)


if __name__ == "__main__":
    unittest.main()
