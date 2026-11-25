"""Experimento local reproduzível, sem modificar os dados operacionais."""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qualityai.ml import QualityPredictor, train_lightweight_model
import cv2

root=Path(sys.argv[1])
output=Path('_tmp/validacao-nova-ia')
output.mkdir(parents=True,exist_ok=True)
samples=[]
for label in ('ok','nok'):
    files=sorted((root/label).glob('*.png'))
    selected=files[::max(1,len(files)//10)][:10]
    samples.extend((p,label) for p in selected)
timings=[]
for run in range(2):
    start=time.perf_counter()
    report=train_lightweight_model(samples,output/'modelo.pt')
    timings.append(time.perf_counter()-start)
predictor=QualityPredictor(output/'modelo.pt')
result=predictor.predict(cv2.imread(str(samples[0][0])))
summary={**report.to_dict(),'tempos_segundos':timings,'inspecao':result.label,
         'regularizacao':predictor.payload.get('regularization_c')}
(output/'resultado.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
