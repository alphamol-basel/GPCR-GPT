#!/usr/bin/python
#-*-coding:utf-8-*-
#Filename: app.py
'''
    This application is designed to show a Knowledge based ChatBot.
    Author: Shiyu Wang
    email: shiyu.wang@alphamol.com
'''

from flask import Flask, render_template, request
import json
import pandas as pd
import openai
import re
import os
import py2neo
from py2neo import Node, Relationship, Graph, Subgraph
from py2neo import NodeMatcher, RelationshipMatcher


reationship_list=["Family","Subfamily","G proteins","Effector","Gtex_tissue","HPA_tissue_low","HPA_tissue_medium","HPA_tissue_high","Functions", \
        "diseases", "endogenous ligands", "drugs", "Pdb", "family", "G_protein_belong"]
node_features_list=["uniprot_id","chembl_id", "TTD_id", "KEGG_id", "wiki", "HPA_id", "uniprot_name", "Genewiki", "Amino_acid", \
        "GeneCard_name", "uniprot_function", "GuidetoImmunopharmacology_id"]
pdb_node_features_list=["name", "resolution", "released_year", "method", "reference_title", "reference_journal", "reference_author"]

# open database
graph = Graph("bolt://localhost:7687/", auth=("neo4j", "kangsijia-neo4j"))
matcher_n = NodeMatcher(graph)
matcher_r = RelationshipMatcher(graph)

#use your own openai api
openai.api_key = "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"

with open("static/name_syno.json") as json_file:
    name_syno_dic=json.load(json_file)

with open("static/name.json") as json_file:
    name_dic=json.load(json_file)


def answer(content):
    previous=[{"role": "system", "content": "You are a helpful assistant."}]
    new_message={"role": "user", "content": content}
    previous.append(new_message)
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k",
        messages=previous,
        temperature=0.5
    )
    return response.choices[0].message.content



def process_question(question):
    for name in name_dic:
        if name.lower() in [q.lower() for q in question.split(" ")]:
            break
    if name == "nd":
        for name in name_syno_dic:
            if name.lower() in [q.lower() for q in question.split(" ")]:
                break
    if name == "nd":
        for name in name_syno_dic:
            if name.lower() in question.lower():
                break
    try:
        uniprot=name_dic[name]
    except:
        uniprot=name_syno_dic[name]

    node_features=[]
    relation_features=[]

    pattern = re.compile(r'\"(.*?)\"')
    node_name_list=pattern.findall(question)

    if "uniprot" in question.lower():
        node_features.append("uniprot_id")
        node_features.append("uniprot_name")
    if "chembl" in question.lower():
        node_features.append("chembl_id")
    if "name" in question.lower():
        node_features.append("uniprot_name")
        node_features.append("GeneCard_name")
        node_features.append("Genewiki")
    if "sequence" in question.lower() or "amino acid" in question.lower():
        node_features.append("Amino_acid")
    if "ttd" in question.lower() or "therapeutic target database" in question.lower():
        node_features.append("TTD_id")
    if "kegg" in question.lower() or "kyoto encyclopedia of genes and genomes" in question.lower():
        node_features.append("KEGG_id")
    if "guide to immunopharmacology" in question.lower() or "guidetoimmunopharmacology" in question.lower():
        node_features.append("GuidetoImmunopharmacology_id")
    if "g protein" in question.lower() or "g-protein" in question.lower():
        relation_features.append("G proteins")
    if "class" in question.lower() or "family" in question.lower():
        relation_features.append("Family")
        relation_features.append("Subfamily")
    if "pdb" in question.lower() or "structure" in  question.lower():
        relation_features.append("Pdb")
    if "disease" in question.lower():
        relation_features.append("diseases")
    if "drug" in question.lower():
        relation_features.append("drugs")
    if "ligand" in question.lower() or "bind" in question.lower():
        relation_features.append("endogenous ligands")
    if "tissue" in question.lower() or "distribution" in question.lower():
        relation_features.append("Gtex_tissue")
        relation_features.append("HPA_tissue_high")
        relation_features.append("HPA_tissue_medium")
        relation_features.append("HPA_tissue_low")
    if "pathway" in question.lower():
        relation_features.append("Effector")
        relation_features.append("Functions")
    if "function" in question.lower():
        node_features.append("uniprot_function")
        relation_features.append("Functions")

    return uniprot, node_features, relation_features, node_name_list

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/', methods=['POST'])
def run_script():
    question=request.form['question']
    output={}
    uniprot, node_features, relation_features, node_name_list = process_question(question)
    if uniprot == "nd":
        #output["ChatGPT answer your question"]=question
        output["ChatGPT answer your question"]=answer(question)
        return render_template('index.html', 
        output=output, 
        question=request.form['question'])
    node = matcher_n.match("receptors").where(uniprot_id=uniprot).first()
    content=[]
    for n_fea in node_features:
        content.append(n_fea+" of this receptor is: "+node[n_fea])
    for r_type in relation_features:
        r_s=matcher_r.match({node}, r_type=r_type)
        tmp=[]
        if r_type == "drugs":
            for r in r_s:
                tmp.append(r.end_node["name"])
                tmp.append(" The identity of this drug is: "+str(r.end_node["name"]))
        elif r_type == "Pdb":
            for r in r_s:
                tmp.append(r.end_node["name"])
                tmp.append(" The resolution of this structure is: "+str(r.end_node["resolution"]))
                tmp.append(" The released year of this structure is: "+str(r.end_node["released_year"]))
                tmp.append(" The experimental method of this structure is: "+str(r.end_node["method"]))
                tmp.append(" The title of references of this structure is: "+str(r.end_node["reference_title"]))
                tmp.append(" The reference journal of this structure is: "+str(r.end_node["reference_journal"]))
                tmp.append(" The reference_author of this structure is: "+str(r.end_node["reference_author"]))
        else:
            for r in r_s:
                tmp.append(r.end_node["name"])
        content.append(r_type+" of this receptor follows:"+";".join(tmp))
    if content==[]:
        for n_fea in node_features_list:
            try:
                content.append(n_fea+" of this receptor is: "+node[n_fea])
            except TypeError as e:
                pass
        question=".\n".join(["\n".join(content), "Summarize the above content.",])
    else:
        question=".\n".join(["\n".join(content),
            "Based on the above content, answer the question:",])+" "+question
    #output["ChatGPT answer your question with the enhanced by GPCR-KG"]=question
    output["ChatGPT answer your question with the enhanced by GPCR-KG"]=answer(question)
    output["Supporting information"]=question
    return render_template('index.html', output=output, question=request.form['question'])

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        return redirect(url_for('index'))
    return render_template('contact.html')


@app.route('/home', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        return redirect(url_for('index'))

    return render_template('index.html')

@app.route('/tutorial', methods=['GET', 'POST'])
def tutorial():
    if request.method == 'POST':
        return redirect(url_for('index'))

    return render_template('tutorial.html')

if __name__ == '__main__':
    app.run(host = '0.0.0.0' ,port = 5000, debug = 'False')
