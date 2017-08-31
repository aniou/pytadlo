
import tkinter as tk
import sys
import fileinput
import os
import pickle
import pprint
import random
import time
#
from collections import Counter
from functools import partial
from lxml import etree
from PIL import Image, ImageTk

pp = pprint.PrettyPrinter(indent=4)

VERSION="1.3"
DATA_DIR='dane'
QUIZ_DIR='testy'
    
class Application(tk.Frame):
    
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.grid(column=0, row=0, padx=10, pady=10, 
                  ipadx=10, ipady=10,
                  sticky=tk.N+tk.E+tk.S+tk.W)
        tk.Grid.rowconfigure(master, 0, weight=1)
        tk.Grid.columnconfigure(master, 0, weight=1)
        
        self.quiz       = {}   # wszystkie pytania
        self.qs         = {}   # statystyki pytan
        self.quiz_name  = None # aktualny quiz (katalog albo plik.csv)
        self.box_number = 0    # aktualny box (0-4)
        self.good       = 0    # wszystkich dobry odp. w tej sesji
        self.bad        = 0    # wszystkych zlych odp. w tej sesji
        self.iteration  = 1    # iteracja - teraz globalna a potem moze boksu?
        self.query_id   = None # ID indywidualnego pytania (string)
        
        self.query_widget_type = 'image' # or 'text' -
        
        self.createWidgets()
                
        return

         
    #########################################################
    ##
    def createWidgets(self):
        """ Uklad widgetow w siatce jest nastepujacy:
             
            q     - obszar pytan, label z obrazkiem lub textarea
            r     - miejsce na wpisanie odpowiedzi
            a     - pole, gdzie pojawia się prawidłowa odpowiedź
            l0-4  - piec przyciskow wybierajacy pudelka
            r0-5  - rozne przyciski funkcyjne
            pr    - menu rozwijane z quizami
            ls    - lewe pole podsumowania
            s     - podsumowanie srodkowe
            rs    - prawe pole podsumowania

               0   1   2   3   4   5   
            0      q   q   q   q         - ten wiersz rozciaga sie na max
            1  l4  q   q   q   q   r0    - a pozostale wiersze juz nie
            2  l3  q   q   q   q   r1
            3  l2  q   q   q   q   r2
            4  l1  q   q   q   q   r3
            5  l0  r   r   r   r   r4
            6  pr  a   a   a   a   r5
            7  ls  s   s   rs  rs  

        """
        # widget do wyswietlania obrazkow
        self.query_image = tk.Label(self, font=('', 18, 'bold'))
        # alternatywny widget do wyswietlania tekstu
        self.query_text  = tk.Text(self, width=36, height=4, wrap=tk.WORD, font=('', 18, 'bold'), relief=tk.FLAT, bg='gray95')
        #self.query_text = tk.Text(self, width=36, height=4, wrap=tk.WORD, font=('', 18, 'bold'), relief=tk.FLAT, bg='lightgreen')
        self.query_text.tag_configure("center", justify='center')
        
        # jeden albo drugi sa w tym samym miejscu - domyslnie startuje img
        self.query_image.grid(column=1,  row=0, columnspan=4, rowspan=5, padx=10)
        
        # XXX - poeksperymentowac z usunieciem sticky tk.E+tk+W dla response i answer
        #       bo przy roznicy w szerokosci query i query_text widac jak sie zmienia
        #       ich dlugosc. Przyciski rozwiazalem ustawiajac im grawitacje na scianki.

        # tu sie wpisuje odpowiedz
        self.response = tk.Entry(self, width=80, justify='center',font=('', 12, 'bold'))
        self.response['state'] = tk.DISABLED
        self.response.grid(column=1, row=5, columnspan=4, padx=10, sticky=tk.E+tk.W)
        self.response.bind('<Return>', self.check_user_answer)
 
        # tu sie pojawia prawidlowa odpowiedz
        self.answer = tk.Text(self, width=80, font=('', 12, ''))
        self.answer['height'] = 4
        self.answer.tag_configure("center", justify='center')
        self.answer.grid(column=1, row=6, columnspan=4, padx=10, sticky=tk.E+tk.W)

        # podsumowanie
        self.lsummary = tk.Label(self)
        self.lsummary.grid(column=0,  row=7)

        self.summary = tk.Label(self)
        self.summary.grid(column=1,  row=7, columnspan=2, sticky=tk.W, padx=10)
        
        self.rsummary = tk.Label(self)
        self.rsummary.grid(column=3, row=7, columnspan=2, sticky=tk.E, padx=10)
         
        # rozwijane menu z nazwami
        self.selected_quiz  = tk.StringVar()
        self.quiz_names     = self.get_quiz_list()
        self.quiz_selection = tk.OptionMenu(self, self.selected_quiz, 
                                            *(self.quiz_names), 
                                            command = self.quiz_selected)
        self.quiz_selection.grid(column=0, row=6, sticky=tk.W)
 
        # szesc przyciskow po lewej
        self.lbtn = list(range(5))
        for nr in range(5):
            self.lbtn[nr] = tk.Button(self)
            self.lbtn[nr]['text'] =  0
            self.lbtn[nr]['height'] = 4
            self.lbtn[nr]['width'] = 20            
            self.lbtn[nr]['command'] = partial(self.start_quiz, nr)
            self.lbtn[nr].grid(column=0, row=5-nr, pady=5, sticky=tk.W)
        
        # szesc przyciskow po prawej
        self.btn = list(range(6))
        for nr in range(6):
            self.btn[nr] = tk.Button(self)
            self.btn[nr]['text'] = "b%s" % nr
            self.btn[nr]['height'] = 4
            self.btn[nr]['width'] = 20            
            self.btn[nr].grid(column=5, row=nr+1, pady=5, sticky=tk.E)
    
        # przypisanie funkcji do przyciskow    
        self.btn[0]['command'] = self.end_quiz
        self.btn[0]["text"] = "ZAKOŃCZ"
        
        # start przez wybranie nazwy z pull-down menu
        self.btn[1]['state'] = tk.DISABLED;
        self.btn[1]['command'] = self.do_not_answer
        self.btn[1]['text'] = 'NASTĘPNE'
        
        # pusty przycisk, bedziemy wyswietlac tu wersje
        self.btn[2]['text'] = "v%s" % VERSION
        self.btn[2]['relief'] = tk.GROOVE    
        self.btn[2]['state'] = tk.DISABLED;
        
        self.btn[3]['command'] = self.do_know
        self.btn[3]['text'] = 'WIEM'
        self.btn[3]['state'] = tk.DISABLED;
        
        self.btn[4]['command'] = self.do_not_know
        self.btn[4]['text'] = 'NIE WIEM'
        self.btn[4]['state'] = tk.DISABLED;
        
        self.btn[5]['command'] = self.show_answer
        self.btn[5]['text'] = 'ODPOWIEDŹ'
        self.btn[5]['state'] = tk.DISABLED;
        
        # ustaw rozciaganie - pierwszy wiersz na max
        tk.Grid.rowconfigure(self, 0, weight=4)    
        for nr in range(1,8):
            tk.Grid.rowconfigure(self, nr, weight=0)
        
        # ...kolumny z przyciskami wolniej, niz tresc
        tk.Grid.columnconfigure(self, 0, weight=1)
        for nr in range(1,5):
            tk.Grid.columnconfigure(self, nr, weight=2)
        tk.Grid.columnconfigure(self, 5, weight=1)
        
        return
       

    ######################################################
    # XXX - co wlasciwie przekazuje mi _value?
    def check_user_answer(self, _value):
        
        response = self.response.get().strip()
        valid_response = self.quiz[self.query_id]['odp'].strip()
        print(response, valid_response)
        if response == valid_response:
            self.btn[3]['state'] = tk.NORMAL
            self.response['bg'] = 'lightgreen'
        else:
            self.btn[4]['state'] = tk.NORMAL
            self.response['bg'] = 'orange'
        return
        
    
    def end_quiz(self):
        if not self.quiz_name is None:
            write_quiz_stats(self.quiz_name, self.qs)
        self.master.destroy()
        sys.exit(0)
           
           
    def get_quiz_list(self):
        """ to moze wyleciec poza obiekt """
        directory = npath(QUIZ_DIR)
        return os.listdir(directory)
        
                     
    def quiz_selected(self, quiz_name):
        """ Callback na wybranie nazwy quizu z menu rozwijanego """
        if not self.quiz_name is None:
            write_quiz_stats(self.quiz_name, self.qs)

        self.quiz      = read_quiz_queries(quiz_name)
        if len(self.quiz) == 0:
            self.quiz_name = None
            self.summary['text'] = 'NIE ZNALEZIONO PYTAN'
            return

        self.quiz_name = quiz_name
        self.qs        = read_quiz_stats(quiz_name, self.quiz)
        self.start_quiz()
        return
           
        
    def show_box_counters(self):
         boxes = Counter([self.qs[x]['box'] for x in self.quiz])
         for nr in range(5):
             self.lbtn[nr]['text'] = boxes.get(nr, 0)
         return
   
   
    def create_quiz_set(self):
        # wybierz pytania z danego pudelka
        self.order = []
        for k in self.quiz:
            if self.qs[k]['box'] == self.box_number:
                self.order.append(k)
                
        if len(self.order) == 0:
            self.btn[3]['state'] = tk.DISABLED;
            self.btn[4]['state'] = tk.DISABLED;
            self.btn[5]['state'] = tk.DISABLED;
            return
        
        random.shuffle(self.order)
        self.quiz_position = 0
        self.total         = len(self.order)
        return
   

    def start_quiz(self, box_number=0):
        self.response['state'] = tk.NORMAL
        self.btn[1]['state'] = tk.NORMAL
        self.btn[5]['state'] = tk.NORMAL
        
        # zaznacz aktualne pudelko wciskajac przycisk na stale
        for a in range(5):   # XXX - zmienic na enumerate czy range(len
            if a == box_number:
                relief = tk.SUNKEN
            else:
                relief = tk.RAISED
            #print(a, box_number, relief)          
            self.lbtn[a]['relief'] = relief
        
        self.box_number = box_number
        self.create_quiz_set()
        
        # wyczyscimy na wszelki
        self.query_image.configure(image = '')
        self.query_image.image = ''
        self.query_image.text = None
        
        self.show_box_counters()
        self.show_question()
        # to nie powinno sie tu znajdowac bo jest wolane po kilka razy
        self.bind('<Configure>',self.resize_window)
        return

        
    def resize_window(self, event):
        # XXX - skomasowac to
        if self.quiz[self.query_id]['type'] == 'image':
            self.show_image()
        else:
            self.show_text()
            
        return

        
    def update_summary(self):
        msg = "%i z %i" % (self.quiz_position+1, self.total)
        self.lsummary['text'] = msg
        
        msg = "odpowiedzi w tej sesji złe: %i dobre: %i" % (self.bad, self.good)
        self.rsummary['text'] = msg
        
        msg = "odpowiedzi na to pytanie złe: %i dobre: %i" % \
              (self.qs[self.query_id]['bad'],
               self.qs[self.query_id]['good'])
        self.summary['text'] = msg
        return
    
    
    def do_not_answer(self):
        self.next_question()
        self.show_question()
        return
   
   
    def do_know(self):
        self.good+=1
        self.qs[self.query_id]['good']+=1
        box = self.qs[self.query_id]['box'] + 1
        if box < 5:
            self.qs[self.query_id]['box']=box
            self.show_box_counters()
            
        self.next_question()
        self.show_question()
        return
   
   
    def do_not_know(self):
        self.bad+=1
        self.qs[self.query_id]['bad']+=1
        self.qs[self.query_id]['box']=0
        self.show_box_counters()
        
        self.next_question()
        self.show_question()
        return
        
           
    def show_answer(self):    
        msg = self.quiz[self.query_id]['odp']
        #self.answer['state'] = tk.NORMAL
        self.answer.delete('1.0', tk.END)
        self.answer.insert('1.0', msg)        
        self.answer.tag_add('center', '1.0', 'end')
        #self.answer['state'] = tk.DISABLED
        
        self.btn[3]['state'] = tk.NORMAL
        self.btn[4]['state'] = tk.NORMAL
        return
    
    
    def next_question(self):    
        # pozycja juz wskazuje na nazstepne
        self.quiz_position+=1
        if self.quiz_position >= len(self.order):
            self.create_quiz_set() # zeruje tez pozycje w kolejce            
            self.iteration+=1
        return
    
    
    def show_question(self):
        if len(self.order) == 0:
            return
            
        self.btn[3]['state'] = tk.DISABLED
        self.btn[4]['state'] = tk.DISABLED
        
        self.response['bg'] = 'white'
        self.response.delete(0, tk.END)
        
        # pokaz pytanie
        self.query_id = self.order[self.quiz_position]
        self.update_summary()
        
        # XXX - skomasowac to
        if self.quiz[self.query_id]['type'] == 'image':
            self.show_image()
        elif self.quiz[self.query_id]['type'] == 'text':
            self.show_text()
        else:
            print("WARN: nie umiem typu %s" % self.quiz[self.query_id]['type'])
                        
        self.answer.delete('1.0', tk.END)
        return

    
    def show_text(self):
        # XXX - rozszerzyc na wiecej, niz dwa typy
        if self.query_widget_type == 'image':
            self.query_image.grid_forget()
            self.query_text.grid(column=1, row=0, columnspan=4, rowspan=5, padx=10, sticky=tk.E+tk.W)
            self.query_widget_type = 'text'
        
        self.query_text['state'] = tk.NORMAL
        self.query_text.delete('1.0', tk.END)
        self.query_text.insert('1.0', self.quiz[self.query_id]['query'])
        self.query_text.tag_add('center', '1.0', 'end')        
        self.query_text['state'] = tk.DISABLED
        return
    
    
    def show_image(self):
        # XXX - rozszerzyc na wiecej, niz dwa typy
        if self.query_widget_type == 'text':
            self.query_text.grid_forget()
            self.query_image.grid(column=1, row=0, columnspan=4, rowspan=5, padx=10)
            self.query_widget_type = 'image'
            
        # wyswietlenie pytania
        fname = self.quiz[self.query_id]['img']

        # rozmiar okienka
        # nie wiem, czy da sie ladniej, ale dla obrazka
        # rozmiar wyswietlania to ok 3/5 w poziomie i 5/7 w pionie
        w = int(self.winfo_width() * 0.6)
        h = int(self.winfo_height() * 0.6)
            
        # robimy thumbnaila a potem i tak podklejamy tlo
        # - to jedyny sposob, zeby zachowac aspect ratio
        # a jednoczesnie zeby nie skakly widgety jesli 
        # jeden z wymiarow bedzie znacznie mniejszy
        image = Image.open(fname)
        (iw, ih) = image.size
        if (iw > w) or (ih > h):
            image.thumbnail((w,h),Image.ANTIALIAS)
 
        (iw, ih) = image.size
        background = Image.new('RGBA', (w,h), (255, 255, 255, 0))
        #background = Image.new('RGBA', (w,h), (255, 255, 255, 255))
        offset=(int((w-iw)/2),int((h-ih)/2))
        background.paste(image,offset)
        photo = ImageTk.PhotoImage(background)
            
        self.query_image.configure(image = photo)
        self.query_image.image = photo
        return


####################################################    
#           
def npath(path, *pathes):
    """ robi jednoczesne path.join i normcase zeby
        skrócić kilometrowe wywołania"""
    return os.path.normcase(os.path.join(path, *pathes))
      



def read_queries_from_kvtml(quiz_name, file_name, qd):
    """
      Odczytuje dane z pliku kvtml, zakładając taką strukturę,
      jak poniżej (szczególnie id='0' lib id='1' w tagu translation

      <entries>
	<entry id="0">
	  <translation id="0">
	    <text>a square</text>
	  </translation>
	  <translation id="1">
	    <text>plac</text>
	  </translation>
	</entry>
	<entry id="1">
        ...
    """
    with open(file_name, 'rb') as xml_doc:
        context = etree.iterparse(xml_doc, events=("start", "end"))
        
        t = [] 
        for event, elem in context:
            if event == 'start':
                if elem.tag == 'entry':
                    #print("start entry id %s" %  elem.get('id'))
                    t = [None, None] # zakladamy tylko translation id=0 i 1
                elif elem.tag == 'translation':
                    t_id = int(elem.get('id'))
                elif elem.tag == 'text':
                    t[t_id] = elem.text
                else:
                    continue

            if event == 'end' and elem.tag == 'entry':
       	        query  = t[0]
                answer = t[1]
                id = "%s/%s" % (quiz_name, query)
                qd[id] = {
                    'img': [],
                    'query': [],
                    'odp': "brak pliku opis.txt w %s" % id
                }

                qd[id]['query'].append(query)
                qd[id]['odp'] = answer

            elem.clear()

    #pp.pprint(qd)
    return

def read_queries_from_csv(quiz_name, file_name, qd):
    """ Odczytuje pary pytanie - odpowiedź z pliku csv
        i dodaje do dictionary przekazanego jako parametr
    """ 

    for line in fileinput.input(file_name, openhook=fileinput.hook_encoded("utf-8")):
        line = line.rstrip('\n')
        t = line.split(',')
        if len(t) < 2:
            print("ERR: bad line %s in %s" % (line, dname))
            continue
        query  = t[0]
        answer = t[1]
        
        id = "%s/%s" % (quiz_name, query)
        #print(id)
        qd[id] = {
            'img': [],
            'query': [],
            'odp': "brak pliku opis.txt w %s" % id
        }

        qd[id]['query'].append(query)
        qd[id]['odp'] = answer
        
    return
      
      
def read_quiz_queries(quiz_name):
    """
    Struktura katalogu jest taka:
    root/obiekt1/zdjecie1,zdjecie2,opis
         obiekt2/zdjecie1,opis
         obiekt3/zdjecie1,zdjecie,opis
         
    - kazdy przypadek root/obiekt/zdjecie jest unikalny, 
      opisy sa wspolne dla root/obiekt/ 
    """
    qd   = {}
    directory = npath(QUIZ_DIR, quiz_name)

    # XXX - TODO - wywalic to nieszczesne 'directory'
    # wczytujemy pliki CSV
    if os.path.isfile(directory) and directory.endswith('.csv'):
        read_queries_from_csv(quiz_name, directory, qd)

    # wczytujemy pliki CSV
    if os.path.isfile(directory) and directory.endswith('.kvtml'):
        print("kasjer dupa")
        read_queries_from_kvtml(quiz_name, directory, qd)

    # wczytujemy zawartosc katalogi    
    if os.path.isdir(directory):
        # tutaj odczytujemy poszczegolne obiekty
        for d in os.listdir(directory):

            dname = npath(directory, d)
            
            # w danym katalogu tez moga byc pliki cvs zeby dalo sie
            # mieszac ze soba zaptania i obrazki
            if os.path.isfile(dname) and dname.endswith('.csv'):
                read_queries_from_csv(quiz_name, dname, qd)
                continue
            
            if os.path.isfile(dname) and dname.endswith('.kvtml'):
                read_queries_from_kvtml(quiz_name, dname, qd)
                continue

            # odczyt katalogu
            if not os.path.isdir(dname): continue
            id = "%s/%s" % (quiz_name, d)
            qd[id] = {
                'img': [],
                'query': [],
                'odp': "brak pliku opis.txt w %s" % id
            }
            
            # jednak katalog, szukamy dobra i piekna
            for f in os.listdir(dname):
                ext = str.lower(f.split('.')[-1:][0])
                fname = npath(dname, f)
                   
                if f == 'opis.txt':                
                    with open (fname, 'r', encoding='utf-8') as myfile:
                        qd[id]['odp']=myfile.read()
            
                if ext in ['jpg', 'png', 'gif']:
                    qd[id]['img'].append((fname,f))


    #pp.pprint(qd)
    # przerabiamy to na gotowe do uzycia ciagi
    qw = {}  # queries
    for id in qd:
        if ((len(qd[id]['img']) == 0) or (len(qd[id]['odp']) == 0)) and (len(qd[id]['query']) == 0):
            #pp.pprint(qd[id])
            print("ERR: niekompletny opis/brak zdjecia w %s" % id)
    
        # XXX to jakos skomasowac dla obu przypadkow    
        for (fname, f) in qd[id]['img']:
            newid = "%s/%s" % (id, f)
            qw[newid] = {
                'img':  fname,
                'type': 'image',
                'odp':  qd[id]['odp']
             }

        # pytanie z jednym slowem             
        for (f) in qd[id]['query']:
            qw[id] = {
                'query': f,
                'type': 'text',
                'odp':   qd[id]['odp']
             }

       
    #pp.pprint(qw)       
    return(qw)

    
def read_quiz_stats(quiz_name, query):
    """ Tworzy liste statystyk na podstawie wczytanych pytan
        i - ewentualnie - zapisanych wczesniej wynikow
    """
    qs    = {}
    qtmp  = {}
    fname = npath(DATA_DIR, quiz_name + '.pickle')
    if os.path.isfile(fname):
        with open(fname, 'rb') as f:
            try :
                qtmp = pickle.load(f)
            except e:
                print("ERR: %s" % e)
                qtmp = {}
    
    for q in query:
        qs[q] = {}
        qs[q]['box']  = qtmp.get(q, {}).get('box',  0)
        qs[q]['good'] = qtmp.get(q, {}).get('good', 0)
        qs[q]['bad']  = qtmp.get(q, {}).get('bad',  0)
            
    return(qs)


def write_quiz_stats(quiz_name, qs):
    """ Zapisuje statystyki pytan do pozniejszego uzycia
    """
    dname = npath(DATA_DIR)
    if not os.path.exists(dname):
        os.mkdir(dname)
    
    fname = npath(DATA_DIR, quiz_name + '.pickle')
    with open(fname, 'wb') as f:
        pickle.dump(qs, f, pickle.HIGHEST_PROTOCOL)

    return

    
####################################################    
#     
def main():    
    random.seed()        
    root = tk.Tk()
    app = Application(master=root)
    app.mainloop()
    sys.exit(0)

if __name__=="__main__":
    main()
