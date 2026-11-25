"""Compara latência de duas arquiteturas locais na mesma tarefa binária."""
from pathlib import Path
import sys
import json
import time
import platform
import statistics
import hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
import torch
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from torchvision.models import resnet18, ResNet18_Weights
from qualityai.ml import QualityPredictor, _frame_to_tensor
from qualityai.preprocessing import apply_filters

def main():
    torch.set_num_threads(4)
    root=Path(sys.argv[1]); model=Path(sys.argv[2]); target=Path(sys.argv[3])
    predictor=QualityPredictor(model)
    samples=[]; labels=[]
    for label in ('ok','nok'):
        paths=sorted((root/label).glob('*.png'))
        for path in paths[::max(1,len(paths)//10)][:10]:
            image=cv2.imread(str(path))
            if image is not None:
                samples.append(image); labels.append(int(label=='ok'))
    baseline=resnet18(weights=ResNet18_Weights.DEFAULT)
    baseline.fc=torch.nn.Identity()
    baseline.requires_grad_(False).eval()
    def embedding(frame):
        prepared=apply_filters(frame,predictor.preprocessing)
        tensor=_frame_to_tensor(prepared,predictor.transform)
        with torch.inference_mode():
            return baseline(tensor).reshape(-1)
    features=np.stack([embedding(frame).numpy() for frame in samples])
    linear=make_pipeline(StandardScaler(),LogisticRegression(class_weight='balanced',solver='liblinear',C=.1))
    linear.fit(features,np.array(labels))
    scaler=linear.steps[0][1]; classifier=linear.steps[1][1]
    mean=torch.tensor(scaler.mean_,dtype=torch.float32)
    scale=torch.tensor(scaler.scale_,dtype=torch.float32).clamp(min=1e-8)
    coef=torch.tensor(classifier.coef_[0],dtype=torch.float32)
    intercept=float(classifier.intercept_[0])
    def conventional(frame):
        vector=embedding(frame)
        return float(torch.sigmoid(torch.dot(coef,(vector-mean)/scale)+intercept))
    calls={'resnet18':conventional,'qualityai':predictor.predict}
    for call in calls.values():
        for i in range(10):call(samples[i%len(samples)])
    times={key:[] for key in calls}
    for repetition in range(5):
        order=list(calls) if repetition%2==0 else list(reversed(calls))
        for key in order:
            for i in range(40):
                frame=samples[i%len(samples)]
                start=time.perf_counter_ns(); calls[key](frame)
                times[key].append((time.perf_counter_ns()-start)/1e6)
    result={'data_local':'2026-11-25','processador':platform.processor(),'threads_torch':4,
            'dispositivo':'CPU','amostras_distintas':len(samples),'repeticoes_por_modelo':200,
            'aquecimento_por_modelo':10,
            'escopo':'Imagem em memória, ROI/filtros, transformação, extração, normalização e classificação. Exclui câmera, disco e carregamento do modelo.',
            'referencia':'ResNet18 pré-treinada e congelada + classificador linear ajustado nas mesmas 20 imagens. Não representa a média do mercado.',
            'modelo_qualityai':str(model),
            'resumo_modelo_sha256':hashlib.sha256(model.read_bytes()).hexdigest(),
            'versao_torch':torch.__version__,
            'tempos_ms':{},'medicoes_individuais_ms':times}
    for key,values in times.items():
        result['tempos_ms'][key]={'mediana':statistics.median(values),'media':statistics.mean(values),'p95':float(np.percentile(values,95))}
    result['razao_mediana']=result['tempos_ms']['resnet18']['mediana']/result['tempos_ms']['qualityai']['mediana']
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='medicoes_individuais_ms'},ensure_ascii=False))

if __name__=='__main__':main()
