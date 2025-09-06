# Kubernetes além do deploy: automação inteligente com K8sGPT e AIOps


## Ambiente local: 

Caso queira testar, provionei um passo a passo simples usando o [Kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation)


### KIND

Criar Cluster:

```
kind create cluster --config kind/ai-cluster.yaml --image=kindest/node:v1.32.5
```
#### MetalLB

MetalLB permitirá que seu cluster KIND tenha IPs de LoadBalancer, já que KIND não tem isso nativamente.

```
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.14.9/config/manifests/metallb-native.yaml
```
Abaixo,  ajuste o range IP para sua rede KIND

```yaml

apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: kind-pool
  namespace: metallb-system
spec:
  addresses:
  - 172.18.0.240-172.18.0.250  # intervalo seguro fora dos IPs dos nodes
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: l2
  namespace: metallb-system

```
kubectl apply -f kind/loadbalancer/metallb-config.yaml


#### Nginx:

Crie o namespace dedicado e instale o ingress NGINX, expondo o serviço como LoadBalancer para receber tráfego externo:

```bash
kubectl create namespace ingress-nginx
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --set controller.service.type=LoadBalancer

```

Caso queira adicionar persistência nesse ambiente acesse https://github.com/silvemerson/kind-infra-lab



### Ollama

Instale o Ollama no seu cluster K8s conforme passo a passo abaixo:

```
helm repo add otwld https://helm.otwld.com/
helm repo update
helm upgrade ollama otwld/ollama --namespace ollama --values values.yaml
```


Configure seu ```/etc/hosts``` de acordo com o IP do service do Nginx

```bash

172.xx.xx.xx ollama.local

```


Valide: 

```bash

curl http://ollama.local
Ollama is running

```