#!/usr/bin/bash

pygst-launch \
    --file=pipeline.gstp \
    --obs=analytics \
    --ext=demo:MyCustomExtract \
    --proc=demo:DDBBWriterProcess
