# PlayStation 2 Controller Analyzer
  
## Getting started

- Download the code of this repository
- In Logic 2, open the Extensions tab on the right
  - In the menu, click "Load Existing Extension..." and select this project's "extension.json" file
- Open the Analyzers tab on the right
  - Add an "SPI" analyzer and select the correct pins and settings (LSB first, 8-bit, CPOL=1, CPHA=1)
  - Add the "PlayStation 2 Controller Analyzer" and select the "SPI" analyzer as input
- Begin capturing or load an existing capture

![Screenshot](https://github.com/kbhomes/ps2-controller-analyzer-saleae-logic/raw/main/docs/logic2-ps2-controller-analyzer.png)
