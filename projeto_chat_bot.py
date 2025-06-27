from gc import disable
from altair import Key
import streamlit as st 
import re
import openai
from pathlib import Path
from unidecode import unidecode
import pickle
import os

from dotenv import load_dotenv, find_dotenv

_= load_dotenv(find_dotenv())

PASTA_CONFIGURACOES = Path(__file__).parent / 'configuracoes'
PASTA_CONFIGURACOES.mkdir(exist_ok=True)
PASTA_MENSAGENS = Path(__file__).parent / 'mensagens'
PASTA_MENSAGENS.mkdir(exist_ok=True)
CACHE_DESCONVERTE = {}


openai_key = os.getenv('OPENAI_API_KEY')

def retorna_respota_modelo(mensagens, openai_key, modelo="gpt-4o-mini", temperatura=0, stream=False):
    openai.api_key = openai_key
    response = openai.chat.completions.create(
        model=modelo,
        messages=mensagens,
        temperature=temperatura,
        stream=stream,
    )
    
    return response



#SALVAMENTO E LEITURA DE CONVERSAS ===========================================================================
def converte_nome_mensagem(nome_mensagem):
    nome_arquivo = unidecode(nome_mensagem)
    nome_arquivo = re.sub('\\W+', '', nome_arquivo).lower()
    return nome_arquivo


def desconverte_nome_mensagem(nome_arquivo):
    if not nome_arquivo in CACHE_DESCONVERTE:
        
        nome_mensagem = ler_mensagem_por_nome_arquivo(nome_arquivo, key='nome_mensagem')
        
        CACHE_DESCONVERTE[nome_arquivo] = nome_mensagem
        
    return CACHE_DESCONVERTE[nome_arquivo]
    


def retorna_nome_da_mensagem(mensagens):
    for mensagem in mensagens:
        if mensagem['role'] == 'user':
            nome_mensagem = mensagem['content'][:30]
            break
    return nome_mensagem
          


def salvar_mensagens(mensagens):
    if len(mensagens) == 0:
        return False
    nome_mensagem = ''
    
    for mensagem in mensagens:
        if mensagem['role'] == 'user':
            nome_mensagem = mensagem['content'][:30]
            break
    
    nome_mensagem = retorna_nome_da_mensagem(mensagens)
    nome_arquivo = converte_nome_mensagem(nome_mensagem)
    arquivo_salvar = {'nome_mensagem': nome_mensagem,
                      'nome_arquivo': nome_arquivo,
                      'mensagem': mensagens}
    
    with open(PASTA_MENSAGENS / nome_arquivo, 'wb') as f:
        pickle.dump(arquivo_salvar, f)
    
    
def ler_mensagem_por_nome_arquivo(nome_arquivo, key='mensagem'):
    with open (PASTA_MENSAGENS / nome_arquivo, 'rb') as f:
        mensagens = pickle.load(f)
    return mensagens[key]
    


def ler_mensagens(mensagens, key='mensagem'):
    if len (mensagens) == 0:
        return []
    
    nome_mensagem = retorna_nome_da_mensagem(mensagens)
    nome_arquivo = converte_nome_mensagem(nome_mensagem)
    with open (PASTA_MENSAGENS / nome_arquivo, 'rb') as f:
        mensagens = pickle.load(f)
        
    return mensagens[key]



def listar_conversas():
    conversas = list(PASTA_MENSAGENS.glob('*'))    
    conversas = sorted(conversas, key=lambda item: item.stat().st_mtime_ns, reverse=True)
    return [c.stem for c in conversas]


# SALVAMENTO DE CHAVE
def salva_chave(chave):
    with open(PASTA_CONFIGURACOES / 'chave', 'wb') as f:
        pickle.dump(chave, f)

def le_chave():
    if (PASTA_CONFIGURACOES / 'chave').exists():
        with open (PASTA_CONFIGURACOES / 'chave', 'rb') as f:
            return pickle.load(f)
    else:
        return ''

def inicializacao():
    if not 'mensagens' in st.session_state:
        st.session_state.mensagens = []
        
    if not 'conversa_atual' in st.session_state:
        st.session_state.conversa_atual = ''
        
    if not 'modelo' in st.session_state:
        st.session_state.modelo = 'gpt-3.5-turbo'
        
    if not 'api_key' in  st.session_state:
        st.session_state.api_key = le_chave()
    
    


# PÁGINAS ====================================================================================================
def pagina_principal():
    
    #Verifica se já existe uma lista de mensagens no session_state memória temporária da conversa com a API 

        
    mensagens = ler_mensagens(st.session_state['mensagens'])
    
    #cabeçalho da interface e exibe o titulo principal
    st.header(' ChatBot 🤖 Project', divider=True)
    
    #pegando cada item da lista 
    for mensagem in mensagens:
        
        #instância de chat como se fosse uma nova linha do nosso chat e a gente diz quem esta conversando
        chat =  st.chat_message(mensagem['role']) #role no caso usuário
        
        #digo o que quero escrever nessa nova linha de conversa e digo content da mensagem ou conversa 
        chat.markdown(mensagem['content'])
        
    prompt = st.chat_input('Fale com o chat') #aqui serve para que o usuario escreva a mensagem 
        
        #nesse if qd usuario nao digita nada ele nao entra, mas se o usuario escreve algo ele entra no if 
    if prompt:
            
            #aqui faz uma nova mensagem de qd o usuario digita e o conteudo dela é o prompt que ele escreveu 
        nova_mensagem = {'role': 'user',
                         'content': prompt}
            
        chat =  st.chat_message(nova_mensagem['role'])
        chat.markdown(nova_mensagem['content'])
            
            #adicionando as mensagens anteriores a nova mensagem do usuário 
        mensagens.append(nova_mensagem)
        
        
        #receber a resposta da openai
        chat = st.chat_message('assistant')
        placeholder = chat.empty()
        
        placeholder.markdown("▌")
        
        resposta_completa = ''
        respostas = retorna_respota_modelo(mensagens, openai_key, modelo=st.session_state['modelo'], stream=True)
        
        for resposta in respostas:
            resposta_completa += resposta.choices[0].delta.content or ''      
            
            placeholder.markdown(resposta_completa + "▌") 
              
        placeholder.markdown(resposta_completa)   
        nova_mensagem = {'role': 'assistant', 'content' : resposta_completa}
        mensagens.append(nova_mensagem)
           
        st.session_state['mensagens'] = mensagens
        salvar_mensagens(mensagens)
        
# FUNÇÕES DE MANIPULAÇÃO DE CONVERSAS ========================================================================
def excluir_conversa(nome_arquivo):
    if (PASTA_MENSAGENS / nome_arquivo).exists():
        os.remove(PASTA_MENSAGENS / nome_arquivo)
        st.session_state['mensagens'] = []
        st.session_state['conversa_atual'] = ''
    else:
        st.error('Conversa não encontrada!')

def tab_conversas(tab):
    tab.button('➕ Nova conversa',
               on_click=seleciona_conversa, 
               args=('',),
               use_container_width=True)
    tab.markdown('')
    conversas = listar_conversas()
    
    for nome_arquivo in conversas:
        nome_mensagem = desconverte_nome_mensagem(nome_arquivo).capitalize()
        if len (nome_mensagem) == 30:
            nome_mensagem += '...'
            
        col1, col2 = tab.columns([0.85, 0.15])
        
        col1.button(
            label=nome_mensagem,
            on_click=seleciona_conversa,
            args=(nome_arquivo,),
            key=f'conversa_{nome_arquivo}',
            disabled = nome_arquivo==st.session_state['conversa_atual'],
            use_container_width=True,                  
        )
        
        col2.button(
            label='🗑️',
            on_click=excluir_conversa,
            args=(nome_arquivo,),
            key=f'deletar_{nome_arquivo}',
            use_container_width=True,
        )
            
        

    

def tab_configuracoes(tab):
    modelo_escolhido = tab.selectbox('Selecione o modelo',
                                     ['gpt-4o-mini', 'gpt-3.5-turbo', 'gpt-4'],)
    
    st.session_state['modelo'] = modelo_escolhido
    
    chave = tab.text_input('Adicione sua chave da OpenAI',value=st.session_state['api_key'], type='password')
    
    if chave != st.session_state['api_key']:
        st.session_state['api'] = chave
        salva_chave(chave)
        tab.success('Chave da OpenAI atualizada com sucesso!')
        



def seleciona_conversa(nome_arquivo):
    if nome_arquivo == '':
        st.session_state.mensagens = []
    else:
        mensagem = ler_mensagem_por_nome_arquivo(nome_arquivo, key='mensagem')
        st.session_state.mensagens = mensagem
    st.session_state['conversa_atual'] = nome_arquivo
    


def main():  
    inicializacao()
    pagina_principal()
    
    
    tab1, tab2 = st.sidebar.tabs(["Conversas", "Configurações"])
    tab_conversas(tab1)
    tab_configuracoes(tab2)
    
    


if __name__ == '__main__':
    main()