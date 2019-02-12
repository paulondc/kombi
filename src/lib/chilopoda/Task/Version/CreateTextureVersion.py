import os
from ..Task import Task
from .CreateIncrementalVersion import CreateIncrementalVersion

class CreateTextureVersion(CreateIncrementalVersion):
    """
    Create texture version task.
    """

    def __init__(self, *args, **kwargs):
        """
        Create a texture version.
        """
        super(CreateTextureVersion, self).__init__(*args, **kwargs)
        self.setOption('maketxArgs', "-v -u --unpremult --oiio")

    def _perform(self):
        """
        Perform the task.
        """
        for crawler in self.crawlers():

            textureOriginalTargetLocation = self.__computeTextureTargetLocation(
                crawler,
                crawler.var('ext')
            )

            # copying the original texture file
            self.copyFile(
                crawler.var('filePath'),
                textureOriginalTargetLocation
            )

            # executing convert texture task
            convertTexureTask = Task.create('convertTexture')
            convertTexureTask.setOption(
                'maketxArgs',
                self.option('maketxArgs')
            )

            textureTxTargetLocation = self.__computeTextureTargetLocation(crawler, "tx")
            convertTexureTask.add(crawler, textureTxTargetLocation)
            convertTexureTask.output()

            # adding texture files to the published version
            self.addFile(textureOriginalTargetLocation)
            self.addFile(textureTxTargetLocation)

        return super(CreateTextureVersion, self)._perform()

    def __computeTextureTargetLocation(self, crawler, ext):
        """
        Compute the target file path for an texture.
        """
        return os.path.join(
            self.dataPath(),
            ext,
            "{0}_{1}.{2}".format(
                crawler.var('mapType'),
                crawler.var('udim'),
                ext
            )
        )


# registering task
Task.register(
    'createTextureVersion',
    CreateTextureVersion
)
