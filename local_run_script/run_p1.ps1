$scriptPath = Split-Path -parent $PSCommandPath;
$algoPath = "$scriptPath\p1_strategy.py"

py -3 $algoPath
