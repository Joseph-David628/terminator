$scriptPath = Split-Path -parent $PSCommandPath;
$algoPath = "$scriptPath\p2_strategy.py"

py -3 $algoPath
