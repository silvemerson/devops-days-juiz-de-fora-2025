#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K8sGPT Cluster Analyzer
Script para executar analises K8sGPT e gerar relatorios tecnicos estruturados
Compativel com Python 3.6+
"""

import json
import subprocess
import datetime
import argparse
import os
import sys
from collections import Counter

# Verificar versao do Python
if sys.version_info < (3, 6):
    print("Erro: Este script requer Python 3.6 ou superior")
    print("Versao atual: {}".format(sys.version))
    sys.exit(1)

class K8sGPTResult(object):
    """Estrutura para armazenar resultados do K8sGPT"""
    def __init__(self, kind, name, error=None, details=None, text=None, parentObject=None):
        self.kind = kind
        self.name = name
        self.error = error
        self.details = details
        self.text = text
        self.parentObject = parentObject
    
    def __repr__(self):
        return "K8sGPTResult(kind='{}', name='{}', error='{}')".format(
            self.kind, self.name, self.error)

class K8sGPTAnalyzer(object):
    """Classe principal para analise K8sGPT e geracao de relatorios"""
    
    def __init__(self, namespace="default", k8sgpt_path="k8sgpt"):
        self.namespace = namespace
        self.k8sgpt_path = k8sgpt_path
        self.timestamp = datetime.datetime.now()
        self.results = []
        
    def check_k8sgpt_installed(self):
        """Verifica se K8sGPT esta instalado e acessivel"""
        try:
            result = subprocess.check_output([self.k8sgpt_path, "version"], 
                                           stderr=subprocess.STDOUT, 
                                           universal_newlines=True)
            return True
        except (subprocess.CalledProcessError, OSError):
            return False
    
    def get_cluster_context(self):
        """Obtem informacoes do contexto do cluster"""
        try:
            # Contexto atual
            try:
                current_context = subprocess.check_output(
                    ["kubectl", "config", "current-context"],
                    stderr=subprocess.STDOUT, universal_newlines=True
                ).strip()
            except subprocess.CalledProcessError:
                current_context = "Unknown"
            
            # Namespace padrao
            try:
                default_namespace = subprocess.check_output(
                    ["kubectl", "config", "view", "--minify", "-o", "jsonpath={..namespace}"],
                    stderr=subprocess.STDOUT, universal_newlines=True
                ).strip() or "default"
            except subprocess.CalledProcessError:
                default_namespace = "default"
            
            # Versao do Kubernetes
            k8s_version = "Unknown"
            try:
                version_output = subprocess.check_output(
                    ["kubectl", "version", "--client=true", "-o", "json"],
                    stderr=subprocess.STDOUT, universal_newlines=True
                )
                version_data = json.loads(version_output)
                k8s_version = version_data.get("clientVersion", {}).get("gitVersion", "Unknown")
            except (subprocess.CalledProcessError, json.JSONDecodeError):
                pass
            
            return {
                "context": current_context,
                "default_namespace": default_namespace,
                "kubernetes_version": k8s_version
            }
        except Exception as e:
            print("Warning: Could not get cluster context: {}".format(e))
            return {"context": "Unknown", "default_namespace": "default", "kubernetes_version": "Unknown"}
    
    def run_k8sgpt_analysis(self, filters=None, explain=True):
        """Executa analise K8sGPT"""
        print("Executando analise K8sGPT no namespace: {}".format(self.namespace))
        
        cmd = [self.k8sgpt_path, "analyze"]
        
        if self.namespace != "all":
            cmd.extend(["--namespace", self.namespace])
        
        if filters:
            cmd.extend(["--filter", ",".join(filters)])
        
        if explain:
            cmd.append("--explain")
        
        cmd.extend(["--output", "json"])
        
        try:
            result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, 
                                           universal_newlines=True)
            
            # Parse do resultado JSON
            try:
                data = json.loads(result)
                self._parse_results(data)
                print("Analise concluida. Encontrados {} itens.".format(len(self.results)))
                return True
            except json.JSONDecodeError as e:
                print("Erro ao fazer parse do JSON: {}".format(e))
                return False
                
        except subprocess.CalledProcessError as e:
            print("Erro ao executar K8sGPT: {}".format(e.output))
            return False
        except Exception as e:
            print("Erro inesperado: {}".format(e))
            return False
    
    def _parse_results(self, data):
        """Faz parse dos resultados JSON do K8sGPT"""
        results = data.get("results", [])
        
        for item in results:
            result = K8sGPTResult(
                kind=item.get("kind", "Unknown"),
                name=item.get("name", "Unknown"),
                error=item.get("error"),
                details=item.get("details"),
                text=item.get("text"),
                parentObject=item.get("parentObject")
            )
            self.results.append(result)
    
    def analyze_results(self):
        """Analisa e categoriza os resultados"""
        if not self.results:
            return {
                "total": 0,
                "by_kind": {},
                "by_severity": {"critical": 0, "warning": 0, "info": 0},
                "critical_issues": [],
                "warnings": [],
                "info": []
            }
        
        # Contagem por tipo
        by_kind = Counter(result.kind for result in self.results)
        
        # Categorizacao por severidade (baseada em palavras-chave)
        critical_keywords = ["crashloopbackoff", "failed", "error", "outofmemory", "evicted"]
        warning_keywords = ["pending", "waiting", "not ready", "warning"]
        
        critical_issues = []
        warnings = []
        info = []
        
        for result in self.results:
            error_text = (result.error or "").lower()
            details_text = (result.details or "").lower()
            combined_text = "{} {}".format(error_text, details_text)
            
            if any(keyword in combined_text for keyword in critical_keywords):
                critical_issues.append(result)
            elif any(keyword in combined_text for keyword in warning_keywords):
                warnings.append(result)
            else:
                info.append(result)
        
        return {
            "total": len(self.results),
            "by_kind": dict(by_kind),
            "by_severity": {
                "critical": len(critical_issues),
                "warning": len(warnings),
                "info": len(info)
            },
            "critical_issues": critical_issues,
            "warnings": warnings,
            "info": info
        }
    
    def generate_markdown_report(self, output_file=None):
        """Gera relatorio tecnico em Markdown"""
        if output_file is None:
            output_file = "k8sgpt-report-{}.md".format(
                self.timestamp.strftime('%Y%m%d-%H%M%S'))
        
        cluster_info = self.get_cluster_context()
        analysis = self.analyze_results()
        
        report_content = self._build_report_content(cluster_info, analysis)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print("Relatorio gerado: {}".format(output_file))
            return output_file
        except Exception as e:
            print("Erro ao salvar relatorio: {}".format(e))
            return None
    
    def _build_report_content(self, cluster_info, analysis):
        """Constroi o conteudo do relatorio Markdown"""
        content = """# K8sGPT Technical Analysis Report

## Executive Summary

**Report Generated:** {}
**Cluster Context:** `{}`
**Kubernetes Version:** `{}`
**Analyzed Namespace:** `{}`

### Key Metrics
- **Total Issues Found:** {}
- **Critical Issues:** {} {}
- **Warnings:** {} {}
- **Informational:** {} {}

### Health Score
{}

## Resource Type Analysis

| Resource Type | Count | Percentage |
|---------------|-------|------------|
""".format(
            self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            cluster_info['context'],
            cluster_info['kubernetes_version'],
            self.namespace,
            analysis['total'],
            u'🔴', analysis['by_severity']['critical'],
            u'🟡', analysis['by_severity']['warning'],
            u'🔵', analysis['by_severity']['info'],
            self._calculate_health_score(analysis)
        )
        
        # Tabela de tipos de recursos
        total = analysis['total']
        if total > 0:
            for kind, count in sorted(analysis['by_kind'].items(), key=lambda x: x[1], reverse=True):
                percentage = (count / float(total)) * 100
                content += "| {} | {} | {:.1f}% |\n".format(kind, count, percentage)
        else:
            content += "| No issues found | 0 | 0% |\n"
        
        # Secoes detalhadas
        content += "\n## Critical Issues\n\n"
        content += self._format_issues_section(analysis['critical_issues'], "critical")
        
        content += "\n## Warnings\n\n"
        content += self._format_issues_section(analysis['warnings'], "warning")
        
        content += "\n## Informational\n\n"
        content += self._format_issues_section(analysis['info'], "info")
        
        # Recomendacoes
        content += self._generate_recommendations(analysis)
        
        # Apendices
        content += self._generate_appendix()
        
        return content
    
    def _calculate_health_score(self, analysis):
        """Calcula score de saude do cluster"""
        total = analysis['total']
        if total == 0:
            return "EXCELLENT (100/100) - No issues detected"
        
        critical = analysis['by_severity']['critical']
        warnings = analysis['by_severity']['warning']
        
        # Formula: 100 - (critical * 20 + warnings * 5)
        score = max(0, 100 - (critical * 20 + warnings * 5))
        
        if score >= 90:
            return "EXCELLENT ({}/100)".format(score)
        elif score >= 70:
            return "GOOD ({}/100)".format(score)
        elif score >= 50:
            return "FAIR ({}/100)".format(score)
        else:
            return "NEEDS ATTENTION ({}/100)".format(score)
    
    def _format_issues_section(self, issues, severity):
        """Formata secao de issues"""
        if not issues:
            return "No {} issues found.\n".format(severity)
        
        content = ""
        for i, issue in enumerate(issues, 1):
            content += "### {}. {}: `{}`\n\n".format(i, issue.kind, issue.name)
            
            if issue.error:
                content += "**Error:** {}\n\n".format(issue.error)
            
            if issue.details:
                content += "**Details:** {}\n\n".format(issue.details)
            
            if issue.text:
                content += "**AI Analysis:**\n{}\n\n".format(issue.text)
            
            if issue.parentObject:
                content += "**Parent Object:** {}\n\n".format(issue.parentObject)
            
            content += "---\n\n"
        
        return content
    
    def _generate_recommendations(self, analysis):
        """Gera secao de recomendacoes"""
        content = "\n## Recommendations\n\n"
        
        total = analysis['total']
        critical = analysis['by_severity']['critical']
        warnings = analysis['by_severity']['warning']
        
        if total == 0:
            content += "**Congratulations!** Your cluster is running smoothly with no issues detected.\n\n"
            content += "### Maintenance Recommendations:\n"
            content += "- Continue monitoring cluster health regularly\n"
            content += "- Consider scheduling periodic health checks\n"
            content += "- Review resource utilization trends\n\n"
        else:
            if critical > 0:
                content += "### Immediate Actions Required:\n"
                content += "- Address all critical issues as priority P0\n"
                content += "- Consider implementing emergency procedures if services are affected\n"
                content += "- Review deployment configurations and resource allocations\n\n"
            
            if warnings > 0:
                content += "### Recommended Actions:\n"
                content += "- Schedule maintenance window to address warnings\n"
                content += "- Review resource requests and limits\n"
                content += "- Consider implementing horizontal pod autoscaling\n\n"
            
            content += "### General Improvements:\n"
            content += "- Implement monitoring and alerting for proactive issue detection\n"
            content += "- Consider using admission controllers for policy enforcement\n"
            content += "- Regular cluster maintenance and updates\n\n"
        
        return content
    
    def _generate_appendix(self):
        """Gera apendice com informacoes adicionais"""
        return """
## Appendix

### Analysis Configuration
- **K8sGPT Version:** Latest
- **Analysis Scope:** {}
- **Timestamp:** {}
- **Total Resources Analyzed:** {}

### Useful Commands
```bash
# Re-run this analysis
{} analyze --namespace {} --explain

# Check specific resource
kubectl get pods -n {}

# View detailed pod information
kubectl describe pod <pod-name> -n {}

# Check logs
kubectl logs <pod-name> -n {}
```

### Legend
- Critical: Immediate attention required
- Warning: Should be addressed soon
- Info: Good to know, low priority

---
*Report generated by K8sGPT Analyzer v1.0*
""".format(
            self.namespace,
            self.timestamp.isoformat(),
            len(self.results),
            self.k8sgpt_path,
            self.namespace,
            self.namespace,
            self.namespace,
            self.namespace
        )

def main():
    """Funcao principal"""
    parser = argparse.ArgumentParser(description="K8sGPT Cluster Analyzer")
    parser.add_argument("-n", "--namespace", default="default", 
                       help="Kubernetes namespace to analyze (default: default)")
    parser.add_argument("-o", "--output", 
                       help="Output file name (default: auto-generated)")
    parser.add_argument("--k8sgpt-path", default="k8sgpt",
                       help="Path to k8sgpt binary (default: k8sgpt)")
    parser.add_argument("--filters", nargs="*", 
                       help="Resource types to filter (e.g., Pod Service)")
    parser.add_argument("--no-explain", action="store_true",
                       help="Skip AI explanations")
    
    args = parser.parse_args()
    
    # Inicializa analyzer
    analyzer = K8sGPTAnalyzer(args.namespace, args.k8sgpt_path)
    
    # Verifica se K8sGPT esta disponivel
    if not analyzer.check_k8sgpt_installed():
        print("K8sGPT nao encontrado. Instale K8sGPT primeiro:")
        print("   brew install k8sgpt")
        print("   # ou baixe de: https://github.com/k8sgpt-ai/k8sgpt/releases")
        sys.exit(1)
    
    # Executa analise
    success = analyzer.run_k8sgpt_analysis(
        filters=args.filters,
        explain=not args.no_explain
    )
    
    if not success:
        sys.exit(1)
    
    # Gera relatorio
    output_file = analyzer.generate_markdown_report(args.output)
    
    if output_file:
        print("Analise concluida com sucesso!")
        print("Relatorio salvo em: {}".format(output_file))
        
        # Mostra resumo no terminal
        analysis = analyzer.analyze_results()
        print("\nResumo:")
        print("   Total de issues: {}".format(analysis['total']))
        print("   Criticos: {}".format(analysis['by_severity']['critical']))
        print("   Warnings: {}".format(analysis['by_severity']['warning']))
        print("   Info: {}".format(analysis['by_severity']['info']))
    else:
        print("Falha ao gerar relatorio")
        sys.exit(1)

if __name__ == "__main__":
    main()