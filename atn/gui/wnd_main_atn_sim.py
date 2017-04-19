#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
---------------------------------------------------------------------------------------------------
wnd_main_atn_sim

janela principal do simulador

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

revision 0.1  2017/mar  matias
initial release (Linux/Python)
---------------------------------------------------------------------------------------------------
"""
__version__ = "$revision: 0.1$"
__author__ = "Ivan Matias"
__date__ = "2017/03"

# < import >---------------------------------------------------------------------------------------

# python library
from PyQt4 import QtGui
from PyQt4 import QtCore
from PyQt4 import QtXml
from string import Template
from core.api import coreapi

import os
import socket
import subprocess
import ConfigParser
import wnd_main_atn_sim_ui as wmain_ui
import dlg_trf as dtraf_ui
import dlg_start as dstart_ui

# < class CWndMainATNSim >-------------------------------------------------------------------------

class CWndMainATNSim(QtGui.QMainWindow, wmain_ui.Ui_CWndMainATNSim):

    # ---------------------------------------------------------------------------------------------
    def __init__(self, f_parent=None):
        # init super class
        super(CWndMainATNSim, self).__init__(f_parent)

        # create main menu ui
        self.setupUi(self)

        # core-gui process
        self.p = None

        # ptracks simulator processes
        self.ptracks = None
        self.adapter = None
        self.visil = None
        self.pilot = None

        self.loadConfigFile()

        self.timer = QtCore.QTimer()

        self.act_stop_session.setEnabled(False)
        self.act_start_dump1090.setEnabled(False)
        self.act_start_visil.setEnabled(False)
        self.act_start_pilot.setEnabled(False)
        self.act_add_aircraft.setEnabled(False)

        self.act_db_edit.setEnabled(False)
        self.act_scenario_to_xml.setEnabled(False)
        self.act_scenario_to_exe.setEnabled(False)


        # create signal and slots connections
        self.act_edit_scenario.triggered.connect(self.cbk_start_edit_mode)
        self.act_start_session.triggered.connect(self.cbk_start_session)
        self.act_stop_session.triggered.connect(self.cbk_stop_session)
        self.act_start_pilot.triggered.connect(self.cbk_start_pilot)
        self.act_start_visil.triggered.connect(self.cbk_start_visil)

        self.act_quit.triggered.connect(QtGui.QApplication.quit)

        #self.act_scenario_to_xml.triggered.connect(self.cbk_scenario_to_xml)

        self.dlg_traf = dtraf_ui.CDlgTraf(f_ptracks_dir=self.ptracks_dir)

        self.dlg_start = dstart_ui.CDlgStart()


    # ---------------------------------------------------------------------------------------------
    def loadConfigFile(self, config="atn-sim-gui.cfg"):
        """
        Faz a leitura de um arquivo de configuração para carregar o diretório do arquivo do cenário
        da simulação criado pelo CORE e do diretório do gerador de informações de alvos ptracks.

        :param config: nome do arquivo de configuração.
        :return:
        """

        if os.path.exists(config):
            conf = ConfigParser.ConfigParser()
            conf.read(config)

            self.scenario_dir = conf.get("Dir", "scenario")
            self.ptracks_dir = conf.get("Dir", "ptracks")
        else:
            self.scenario_dir = os.path.join(os.environ['HOME'], 'atn-sim/configs/scenarios')
            self.ptracks_dir = os.path.join(os.environ['HOME'], 'ptracks')

        self.ptracks_data_dir = os.path.join(self.ptracks_dir, 'data')


    # ---------------------------------------------------------------------------------------------
    def diff_files(self, f_file1, f_file2):
        """
        Verifica a diferença entre os arquivos f_file1 e f_file2.

        :param f_file1:
        :param f_file1:
        :return: retorna True se os arquivos forem diferentes caso contrário False.
        """
        if not os.path.isfile(f_file1) or not os.path.isfile(f_file2):
            return True

        l_diff_proc = subprocess.Popen(['diff', '-q', f_file1, f_file2],
                                stdout=subprocess.PIPE)
        stdout_value = l_diff_proc.communicate()[0]

        if 0 != len(stdout_value):
            return True

        return False


    # ---------------------------------------------------------------------------------------------
    def check_process(self):
        """
        Cria um timer de 100ms para verificar se o processo iniciado foi finalizado pela sua GUI.

        :return:
        """
        QtCore.QObject.connect(self.timer, QtCore.SIGNAL('timeout()'), self.cbk_check_process)
        self.timer.start(100)


    # ---------------------------------------------------------------------------------------------
    def cbk_check_process(self):
        """
        Callback para verificar se a core-gui foi finalizado pela sua GUI.

        :return:
        """
        l_ret_code = self.p.poll()
        if l_ret_code is not None:
            self.statusbar.clearMessage()
            self.timer.stop()

            if self.act_start_session.isEnabled() is False:
                self.act_start_session.setEnabled(True)

            if self.act_edit_scenario.isEnabled() is False:
                self.act_edit_scenario.setEnabled(True)

            # Desabilita as ações para uma simulação ATN ativa
            self.act_stop_session.setEnabled(False)
            self.act_start_dump1090.setEnabled(False)
            self.act_start_visil.setEnabled(False)
            self.act_start_pilot.setEnabled(False)
            self.act_add_aircraft.setEnabled(False)

            # Finaliza o adapter do ptracks para o core-gui
            if self.adapter:
                kill = "kill -9 $(pgrep -P " + str(self.adapter.pid) + ")"
                os.system(kill)
                self.adapter.terminate()

            # Finaliza o ptracks
            if self.ptracks:
                kill = "kill -9 $(pgrep -P " + str(self.ptracks.pid) + ")"
                os.system(kill)
                self.ptracks.terminate()

            # Finaliza a visualização do ptracks
            if self.visil:
                kill = "kill -9 $(pgrep -P " + str(self.visil.pid) + ")"
                os.system(kill)
                self.visil.terminate()

            # Finaliza o piloto do ptracks
            if self.pilot:
                kill = "kill -9 $(pgrep -P " + str(self.pilot.pid) + ")"
                os.system(kill)
                self.pilot.terminate()


    # ---------------------------------------------------------------------------------------------
    def cbk_start_edit_mode(self):
        """
        Inicia a core-gui no modo de edição.

        :return:
        """
        # Se exitir algum processo iniciado e não finalizado, termina seu processamento.
        if self.p:
            l_ret_code = self.p.poll()
            if l_ret_code is None:
                self.p.terminate()

        # Inicia o core-gui no modo de edição
        self.p = subprocess.Popen(['core-gui'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        # Apresenta a mensagem na barra de status da GUI
        self.statusbar.showMessage("Starting core-gui in edit mode!")

        # Timer para verificar se o processo foi finalizado pelo core-gui.
        self.check_process()

        # Desabilitar a ação de iniciar a simulação
        self.act_start_session.setEnabled(False)
        self.act_edit_scenario.setEnabled(False)


    # ---------------------------------------------------------------------------------------------
    def cbk_start_session(self):
        """
        Inicia a simulação de um determinado cenário de simulação. Verifica se existem os arquivos
        necessários para execução do ptracks. Caso não existam é dado a possibilidade de
        criá-los.

        :return:
        """

        # Seleciona o arquivo cenário de simulação em XML
        l_file_path = QtGui.QFileDialog.getOpenFileName(self, 'Open simulation scenario - XML',
                                                        self.scenario_dir, 'XML files (*.xml)')

        # Nenhum arquivo selecionado, termina o processamento
        if not l_file_path:
            return

        # Obtém o nome do arquivo do cenário de simulação sem a extensão.
        self.filename = os.path.splitext(os.path.basename(str(l_file_path)))[0]

        # Monta o diretório de arquivos do ptracks
        l_exe_filename = self.ptracks_data_dir + "/exes/" + self.filename  + ".exe.xml"

        # Cria o arquivo de exercicio para o cenário escolhido caso ele não exista.
        if not os.path.isfile(l_exe_filename):
            self.create_ptracks_exe(l_exe_filename)

        # Monta o nome do arquivo de tráfego do ptracks para o cenário de simulação escolhido
        l_traf_filename = self.ptracks_data_dir + "/traf/" + self.filename + ".trf.xml"

        # Não existe um arquivo de tráfego para o cenário de simulação escolhido, cria ...
        if not os.path.isfile(l_traf_filename):
            l_ret_val = self.create_new_ptracks_traf( l_file_path, l_traf_filename )

            # Arquivo de tráfego para o ptracks não foi criado, abandona a execução do
            # cenário de simulação
            if not l_ret_val:
                return
        else:
            # Arquivo dos tráfegos existe, primeiro cria um arquivo de trafego temporário ...
            self.dlg_traf.populate_table(self.extract_anvs(l_file_path))
            l_tmp_traf_filename = os.path.join(os.environ['HOME'], 'atn-sim/atn/gui') + "/" \
                                  + self.filename + ".trf.xml"
            self.create_ptracks_traf(self.dlg_traf.get_data(), l_tmp_traf_filename)

            # Compara com o arquivo que já existe para verificar se existe alguma diferença
            if self.diff_files(l_traf_filename, l_tmp_traf_filename):
                self.dlg_start.set_title(self.filename)
                l_ret_val = self.dlg_start.exec_()

                # Cancelamento da execução do cenário de simulação
                if QtGui.QDialog.Rejected == l_ret_val:
                    return

                # Cria um novo arquivo de aeronaves
                if 1 == l_ret_val:
                    l_ret_val = self.create_new_ptracks_traf ( l_file_path, l_traf_filename )

                    if not l_ret_val:
                        return ;

        # Monta o nome da sessão que será executada no core-gui
        l_split = l_file_path.split('/')
        self.session_name = l_split [ len(l_split) - 1 ]

        # Executa o core-gui
        self.p = subprocess.Popen(['core-gui', '--start', l_file_path ],
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        # Executar o ptracks .....
        l_cur_dir = os.getcwd()
        os.chdir(self.ptracks_dir)

        self.adapter = subprocess.Popen(['python', 'adapter.py'], stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)
        print "Adapter PID :", self.adapter.pid

        self.ptracks = subprocess.Popen(['python', 'newton.py', '-e', self.filename],
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print "PTRACKS PID :", self.ptracks.pid

        os.chdir(l_cur_dir)

        # Apresenta as mensagens na barra de status
        l_status_msg = "Running the scenario: " + self.filename
        self.statusbar.showMessage(l_status_msg)

        # Timer para verificar se o processo foi finalizado pelo core-gui.
        self.check_process()

        # Desabilita as ações de criar cenario e iniciar a simulação ATN
        self.act_edit_scenario.setEnabled(False)
        self.act_start_session.setEnabled(False)

        # Habilita as ações para uma simulação ATN ativa
        self.act_stop_session.setEnabled(True)
        self.act_start_dump1090.setEnabled(True)
        self.act_start_visil.setEnabled(True)
        self.act_start_pilot.setEnabled(True)
        self.act_add_aircraft.setEnabled(True)


    # ---------------------------------------------------------------------------------------------
    def create_new_ptracks_traf ( self, f_scenario_file, f_traf_filename ):
        """
        A partir de um cenário de simulação, criado pelo core-gui pelo modo de edição, cria um
        arquivo de tráfegos, em XML, para o sistema do ptracks (cinemática das aeronaves da simulação).

        :param f_scenario_file: arquivo do cenário de simulação.
        :param f_traf_filename: arquivo de tráfegos para o ptracks.
        :return: True se o arquivo de tráfegos foi criado com sucesso caso contrário False.
        """

        # Extrai as informações do arquivo do cenário de simulação e popula a tabela da
        # janela de diálogo de aeronaves
        self.dlg_traf.populate_table ( self.extract_anvs ( f_scenario_file ) )

        # Coloca o nome do arquivo do cenário de simulação na barra de título da janela de diálogo.
        self.dlg_traf.set_title(self.filename)

        # Abre a janela de diálogo
        l_ret_val = self.dlg_traf.exec_()

        # Verifica o código de retorno da janela de diálogo, caso desista da operação
        # Avisa o usuário do erro de criação do arquivo de tráfegos.
        if QtGui.QDialog.Rejected == l_ret_val:
            l_msg = QtGui.QMessageBox()
            l_msg.setIcon(QtGui.QMessageBox.Critical)
            l_msg_text = "Error creating file: %s" % f_traf_filename
            l_msg.setText(l_msg_text)
            l_msg.setWindowTitle("Start Session")
            l_msg.setStandardButtons(QtGui.QMessageBox.Ok)
            l_msg.exec_()

            return False
        else:
            # Cria o arquivo de tráfegos para o ptracks.
            self.create_ptracks_traf(self.dlg_traf.get_data(), f_traf_filename )
            return True


    # ---------------------------------------------------------------------------------------------
    def cbk_stop_session(self):
        """
        Stop running session

        :return:
        """
        # Monta a mensagem para solicitar as sessões que estão sendo executadas no CORE
        l_num = '0'
        l_flags = coreapi.CORE_API_STR_FLAG
        l_tlv_data = coreapi.CoreSessionTlv.pack(coreapi.CORE_TLV_SESS_NUMBER, l_num)
        l_msg = coreapi.CoreSessionMessage.pack(l_flags, l_tlv_data)

        # Socket para comunicação com o CORE, conecta-se ao CORE e envia a mensagem
        l_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        l_sock.connect(('localhost', coreapi.CORE_API_PORT))
        l_sock.send(l_msg)

        # Espera a resposta do CORE
        l_hdr = l_sock.recv(coreapi.CoreMessage.hdrsiz)
        l_msg_type, l_msg_flags, l_msg_len = coreapi.CoreMessage.unpackhdr(l_hdr)
        l_data = ""

        if l_msg_len:
            l_data = l_sock.recv(l_msg_len)

        # Desempacota a mensagem do CORE
        l_msg = coreapi.CoreMessage(l_msg_flags, l_hdr, l_data)
        l_sessions = l_msg.gettlv(coreapi.CORE_TLV_SESS_NUMBER)
        l_names = l_msg.gettlv(coreapi.CORE_TLV_SESS_NAME)

        # Cria uma lista de strings com os identificadores das sessões que estão sendo executadas.
        l_lst_session = l_sessions.split('|')

        # Existem nomes para as sessões ?
        if l_names != None:
            # Cria uma lista com os nomes das sessões que estão sendo executadas.
            l_lst_names = l_names.split('|')
            l_index = 0
            while True:
                # Tenta encontrar o nome da sessão que está sendo executada
                if l_lst_names [ l_index ] == self.session_name:
                    break
                l_index += 1

            # Monta a mensagem para finalizar a sessão no CORE
            l_num = l_lst_session [ l_index ]
            l_flags = coreapi.CORE_API_DEL_FLAG
            l_tlv_data = coreapi.CoreSessionTlv.pack(coreapi.CORE_TLV_SESS_NUMBER, l_num)
            l_msg = coreapi.CoreSessionMessage.pack(l_flags, l_tlv_data)
            l_sock.send(l_msg)

        l_sock.close()

        # Finaliza a visualização do ptracks
        if self.visil:
            kill = "kill -9 $(pgrep -P " + str(self.visil.pid) + ")"
            print "Finalizando o visil [%s]" % kill
            os.system(kill)
            self.visil.terminate()

        # Finaliza o piloto do ptracks
        if self.pilot:
            kill = "kill -9 $(pgrep -P " + str(self.pilot.pid) + ")"
            print "Finalizando o piloto [%s]" % kill
            os.system(kill)
            self.pilot.terminate()

        # Finaliza a core-gui
        if self.p:
            self.timer.stop()
            self.p.terminate()

        # Finaliza o adapter do ptracks para o core-gui
        if self.adapter:
            kill = "kill -9 $(pgrep -P " + str(self.adapter.pid) + ")"
            print "Finalizando o adpater [%s]" % kill
            os.system(kill)
            self.adapter.terminate()

        # Finaliza o ptracks
        if self.ptracks:
            kill = "kill -9 $(pgrep -P " + str(self.ptracks.pid) + ")"
            print "Finalizando o ptracks [%s]" % kill
            os.system(kill)
            self.ptracks.terminate()


        # Limpa a barra de status da GUI
        self.statusbar.clearMessage()

        # Habilita as ações de criar cenario e iniciar a simulação ATN
        self.act_edit_scenario.setEnabled(True)
        self.act_start_session.setEnabled(True)

        # Habilita as ações para uma simulação ATN ativa
        self.act_stop_session.setEnabled(False)
        self.act_start_dump1090.setEnabled(False)
        self.act_start_visil.setEnabled(False)
        self.act_start_pilot.setEnabled(False)
        self.act_add_aircraft.setEnabled(False)


    # ---------------------------------------------------------------------------------------------
    def cbk_start_pilot(self):
        """
        Inicia o piloto do ptracks
        :return:
        """
        # Muda para o diretório onde o sistema do ptracks se encontra
        l_cur_dir = os.getcwd()
        os.chdir(self.ptracks_dir)

        # Executa o piloto
        self.pilot = subprocess.Popen(['python', 'piloto.py'], stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)
        print "PILOTO PID", self.pilot.pid

        # Retorna para o diretório do simulador ATN
        os.chdir(l_cur_dir)


    # ---------------------------------------------------------------------------------------------
    def cbk_start_visil(self):
        """
        Inicia a visualização do ptracks
        :return:
        """
        # Muda para o diretório onde o sistema do ptracks se encontra
        l_cur_dir = os.getcwd()
        os.chdir(self.ptracks_dir)

        # Executa o piloto
        self.visil = subprocess.Popen(['python', 'visil.py'], stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)
        print "VISIL PID", self.visil.pid

        # Retorna para o diretório do simulador ATN
        os.chdir(l_cur_dir)


    # ---------------------------------------------------------------------------------------------
    def cbk_scenario_to_xml(self):
        """

        :return:
        """
        pass


    # ---------------------------------------------------------------------------------------------
    def create_ptracks_exe(self, f_scenario_filename):
        """
        Cria o arquivo exe do ptracks para o cenário solicitado

        :param f_scenario_filename: o nome do cenário de simulação
        :return:
        """
        # open template file (exercicio)
        l_file_in = open("templates/exe.xml.in")

        # read it
        l_src = Template(l_file_in.read())

        # document data
        l_title = "ATN Simulator"
        l_hora = "06:00"
        l_data = {"title": l_title, "exe": self.filename, "hora": l_hora}

        # do the substitution
        result = l_src.substitute(l_data)

        # grava o arquivo de exercícios
        with open(f_scenario_filename, 'w') as f:
            f.write(result)


    # ---------------------------------------------------------------------------------------------
    def create_ptracks_traf(self, f_result_set, f_traf_filename):
        """
        Cria um arquivo de tráfegos para po ptracks

        :param f_result_set: lista de dicionários com as informações necessárias para criar o tráfego.
        :param f_traf_filename: o nome do aquivo de tráfegos para o ptracks.
        :return:
        """

        # open template file (trafegos)
        l_file_in = open("templates/trf.xml.in")

        # read it
        l_src = Template(l_file_in.read())

        # document data
        l_data = {"trafegos": '\n'.join(f_result_set)}

        # do the substitution
        l_result = l_src.substitute(l_data)

        with open(f_traf_filename, 'w') as l_file:
            l_file.write(l_result)


    # ---------------------------------------------------------------------------------------------
    def extract_anvs(self, f_xml_filename):
        """
        Extrai as aeronaves que foram criadas pelo core-gui.

        :param f_xml_filename: nome do arquivo XML.
        :return:
        """
        # cria o QFile para o arquivo XML
        l_data_file = QtCore.QFile(f_xml_filename)
        assert l_data_file is not None

        # abre o arquivo XML
        l_data_file.open(QtCore.QIODevice.ReadOnly)

        # cria o documento XML
        l_xdoc_aer = QtXml.QDomDocument("scenario")
        assert l_xdoc_aer is not None

        l_xdoc_aer.setContent(l_data_file)

        # fecha o arquivo
        l_data_file.close()

        # obtém o elemento raíz do documento
        l_elem_root = l_xdoc_aer.documentElement()
        assert l_elem_root is not None

        l_index = 0

        # cria uma lista com os elementos
        l_node_list = l_elem_root.elementsByTagName("host")

        l_table_list = []

        # para todos os nós na lista...
        for li_ndx in xrange(l_node_list.length()):

            l_element = l_node_list.at(li_ndx).toElement()
            assert l_element is not None

            if "host" != l_element.tagName():
                continue

            # read identification if available
            if l_element.hasAttribute("id"):
                ls_host_id = l_element.attribute("id")

            # obtém o primeiro nó da sub-árvore
            l_node = l_element.firstChild()
            assert l_node is not None

            lv_host_ok = False

            # percorre a sub-árvore
            while not l_node.isNull():
                # tenta converter o nó em um elemento
                l_element = l_node.toElement()
                assert l_element is not None

                # o nó é um elemento ?
                if not l_element.isNull():
                    if "type" == l_element.tagName():
                        if "aircraft" == l_element.text():
                            # faz o parse do elemento
                            lv_host_ok = True

                        else:
                            break

                    if "point" == l_element.tagName():
                        # faz o parse do elemento
                        lf_host_lat = float(l_element.attribute("lat"))
                        lf_host_lng = float(l_element.attribute("lon"))

                    if "alias" == l_element.tagName():
                        if l_element.hasAttribute("domain"):
                            if "COREID" == l_element.attribute("domain"):
                                li_ntrf = int(l_element.text())

                # próximo nó
                l_node = l_node.nextSibling()
                assert l_node is not None

            # achou aircraft ?
            if lv_host_ok:

                l_table_item = { "node": str(ls_host_id), "latitude": lf_host_lat, "longitude": lf_host_lng,
                                 "designador": "B737", "ssr": str(7001 + l_index),
                                 "indicativo": "{}X{:03d}".format(str(ls_host_id[:3]).upper(), l_index + 1),
                                 "origem": "SBGR", "destino": "SBBR", "proa": 60, "velocidade": 500,
                                 "altitude": 2000, "procedimento": "TRJ200", "id": str(li_ntrf) }


                l_table_list.append ( l_table_item )

                # incrementa contador de linhas
                l_index += 1

        return l_table_list


# < the end>---------------------------------------------------------------------------------------