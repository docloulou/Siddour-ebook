"""Mise en page de lecture : relie chaque consigne au passage qu'elle concerne."""
from __future__ import annotations

import html
import re

from .hebreu import HE_RE, clean_markup, find_hebrew, outer_units, parse_paragraph, plain_hebrew
from .phonetique import translit

def _merge_prayers(items):
    result=[]
    for kind,text in items:
        if not text.strip():continue
        if kind=='prayer' and result and result[-1][0]=='prayer':result[-1]=('prayer',result[-1][1]+' '+text.strip())
        else:result.append((kind,text.strip()))
    return result

def _anchor(text,tail=False):
    words=text.strip(' ()').split()
    excerpt=' '.join(words[-6:] if tail else words[:6])
    return translit(excerpt).strip(' ()')[:100]

def _condition(text):
    return bool(re.match(r'^(?:À |En été|En hiver|Le Chabbat|Un jour|Les jours|Lors |Pendant |S’il |Si |Pour |Certains |Une femme|L’invité|Au repas)',text))

def _technical(text):
    return bool(re.search(r'initiales|valeur numérique|acrostiche|permutation|combinaison des Noms|lettre youd',text,re.I))

def _brief_rubric(text):
    """Raccourcit uniquement les consignes simples, sans changer leurs conditions."""
    value=text.strip()
    simple={
        'Pendant les dix jours de pénitence, dire :':'Dix jours de pénitence',
        'Le Chabbat, dire :':'Chabbat', 'Le Chabbat :':'Chabbat',
        'À ’Hanouka, dire :':'’Hanouka', 'À Pourim, dire :':'Pourim',
        'À ’Hanouka et Pourim, dire :':'’Hanouka et Pourim',
        'Un jour de fête.':'Yom tov', 'Dans la soucca.':'Dans la soucca',
        'À Roch ’Hodech :':'Roch ’Hodech', 'À Pessa’h :':'Pessa’h',
        'À Chavouot :':'Chavouot', 'À Souccot :':'Souccot',
        'À Roch ’Hodech, les jours de fête et à ’Hol hamoèd, dire :':'Roch ’Hodech, Yom tov et ’Hol hamoèd',
        'Pendant la répétition de l’Amida, dire :':'Répétition de l’Amida',
    }
    return simple.get(value,value)

class ReadingLayout:
    def __init__(self,title,paragraphs,mode,ref,consignes):
        self.mode=mode;self.ref=ref;self.c=consignes
        self.title=title;self.records=[];self.notes=[]
        self.is_amida=('Amida' in self.ref or 'Amidah' in self.ref or 'Mussaf' in self.ref)
        self.is_meal=self.ref=='Post Meal Blessing'
        self.in_zimoun=False
        for i,raw in enumerate(paragraphs):
            kind,segs=parse_paragraph(raw);text=' '.join(t for t,_ in segs)
            self.records.append({'i':i,'raw':raw,'kind':kind,'text':text,'plain':plain_hebrew(text)})

    def prayer(self,text,marker=''):
        text=text.strip()
        if not text or not HE_RE.search(text):return ''
        def opening(body):
            if body.startswith('<'):return body
            first,space,rest=body.partition(' ')
            return '<strong>'+first+'</strong>'+space+rest
        marker='<span class="note-markers" dir="ltr">'+marker+'</span>' if marker else ''
        he='<p class="he" lang="he" dir="rtl">'+opening(self.c.recitation_html(text))+marker+'</p>'
        ph='<p class="ph" lang="fr" dir="ltr">'+opening(self.c.recitation_html(text,True))+(marker if self.mode!='bilingue' else '')+'</p>'
        if self.mode=='hebreu':return he
        if self.mode=='phonetique':return ph
        return '<div class="pair">'+he+ph+'</div>'

    def note(self,text,label='',target='',after=False):
        if not re.search(r'\w',text):return ''
        # Le placement fait le lien avec la prière. Ne pas en recopier l'incipit.
        generic=('Avant le passage','Pendant le passage','Pendant ce passage',
                 'Pour le passage','Après ce passage','Au passage indiqué',
                 'Condition','Choix de la formule')
        if label.startswith(generic):label=''
        if after and not label:label='Après ce passage'
        text=_brief_rubric(text)
        return '<div class="instruction '+('after' if after else 'before')+'" lang="fr" dir="ltr">'+('<span class="label">'+html.escape(label)+'</span>' if label else '')+html.escape(text)+'</div>'

    def footnote(self,text,target):
        n=len(self.notes)+1;self.notes.append((n,text,_anchor(target,True)))
        return '<a class="note-ref" id="appel-'+str(n)+'" href="#note-'+str(n)+'">['+str(n)+']</a>'

    def box(self,body,label,rule='',resume='',href='',css='addition'):
        end=''
        if resume and href:
            end='<p class="resume"><a href="'+html.escape(href)+'">Suite de la prière</a></p>'
        return '<div class="'+css+'">'+('<p class="card-head">'+html.escape(label)+'</p>' if label else '')+('<p class="card-rule">'+html.escape(rule)+'</p>' if rule else '')+body+end+'</div>'

    def insertion(self,body,condition):
        return '<div class="insertion"><p class="card-head">'+html.escape(_brief_rubric(condition))+'</p>'+body+'</div>'

    def optional_prayer(self,text):
        # Un mot facultatif ne doit pas fragmenter la phrase en trois paragraphes.
        rendered=self.prayer(text)
        return re.sub(r'\[([^\[\]<>]+)\]',r'<span class="optional-word">[\1]</span>',rendered)

    def next_prayer(self,index):
        for r in self.records[index:]:
            if r['kind']=='heading':continue
            for k,t in self.items(r):
                if k=='prayer' and HE_RE.search(t):return r['i'],t
        return None,''

    def items(self,r):
        self.c.where=(self.ref,r['i'])
        kind,segs=parse_paragraph(r['raw'])
        if kind=='note':return _merge_prayers(self.c.split(' '.join(t for t,_ in segs)))
        result=[]
        for text,note in segs:result.extend(self.c.split(text) if note else [('prayer',text)])
        return _merge_prayers(result)

    def record_body(self,r):
        return '<div id="p-'+str(r['i'])+'">'+self.paragraph(r)+'</div>'

    def render_item_sequence(self,items):
        items=_merge_prayers(items);parts=[]
        for pos,(kind,text) in enumerate(items):
            if kind=='prayer':parts.append(self.prayer(text));continue
            following=next((t for k,t in items[pos+1:] if k=='prayer'),'')
            previous=next((t for k,t in reversed(items[:pos]) if k=='prayer'),'')
            after=bool(re.match(r'^(?:Deux fois|Trois fois|Sept fois|Répéter|Fin du|Jusqu’ici)',text))
            label='Pour le passage ci-dessus' if after else ('Pendant ce passage' if re.search(r'au mot|s’incliner|à voix basse|toucher|passer les|embrasser',text,re.I) else 'Avant le passage ci-dessous')
            parts.append(self.note(text,label,previous if after else following,after))
        return ''.join(parts)

    def conditional_items(self,items,label='',resume='',href=''):
        # La condition est le seul titre. Aucune étiquette générique supplémentaire.
        items=list(items);condition=''
        while items and items[0][0]=='instruction':
            _,text=items.pop(0)
            if re.search(r'\w',text):condition+=' '+text
        body=self.render_item_sequence(items)
        return self.box(body,_brief_rubric(condition.strip()) or label,resume=resume,href=href)

    def paragraph(self,r):
        self.c.where=(self.ref,r['i'])
        # Parenthèses contenant une condition : elles désignent un ajout ou un remplacement,
        # et non une deuxième phrase à lire après la formule ordinaire.
        raw=r['raw']
        if self.in_zimoun:
            raw=re.sub(r'<small>\(בעשרה ויותר:\s*<b>(.*?)</b>\)\s*</small>',r'[\1]',raw)
        paren=re.compile(r'\(<small>(.*?)</small>\s*([^()]*)\)',re.S)
        units=[];pos=0
        for match in paren.finditer(raw):
            units.extend(outer_units(raw[pos:match.start()]))
            units.append(('parenthesis',(clean_markup(match[1]),clean_markup(match[2]))));pos=match.end()
        units.extend(outer_units(raw[pos:]))
        parts=[];buffer='';before=[];after=[];markers=''
        def flush():
            nonlocal buffer,before,markers
            if HE_RE.search(buffer):
                for text,label,target in before:parts.append(self.note(text,label,target or buffer))
                parts.append(self.optional_prayer(buffer) if self.in_zimoun else self.prayer(buffer,markers))
            else:
                for text,label,target in before:parts.append(self.note(text,label,target))
            buffer='';before=[];markers=''
        for pos,(unit,value) in enumerate(units):
            if unit=='main':buffer+=' '+value;continue
            if unit=='parenthesis':
                cond,prayer=value;fr=self.c.instruction(cond)
                # Magdil/Migdol : remplacement du premier mot, explicitement signalé.
                if plain_hebrew(prayer)=='מגדול' and plain_hebrew(buffer).strip()=='מגדיל':
                    normal=buffer;buffer='';flush()
                    body='<p class="alternative-label">Formule habituelle</p>'+self.prayer(normal)+'<p class="alternative-label">'+html.escape(_brief_rubric(fr))+'</p>'+self.prayer(prayer)
                    parts.append(self.box(body,'Choisir une seule formule',css='choice'))
                else:
                    flush();parts.append(self.insertion(self.prayer(prayer),fr))
                    if self.in_zimoun and pos+1<len(units) and units[pos+1][0]=='main' and HE_RE.search(units[pos+1][1]):
                        parts.append('<p class="join-label">Suite pour tous</p>')
                continue
            items=_merge_prayers(self.c.split(value))
            instructions=[t for k,t in items if k=='instruction' and re.search(r'\w',t)]
            prayers=[t for k,t in items if k=='prayer']
            if not instructions:
                buffer+=' '+' '.join(prayers);continue
            if not prayers:
                text=' '.join(instructions)
                if _technical(text):markers+=self.footnote(text,buffer);continue
                following=next((v for k,v in units[pos+1:] if k=='main' and HE_RE.search(v)),'')
                is_after=bool(re.match(r'^(?:Deux fois|Trois fois|Sept fois|Répéter|Fin du|Jusqu’ici)',text))
                if is_after:after.append((text,buffer))
                else:
                    # Une consigne gestuelle reste à son emplacement exact, sans citation.
                    flush();parts.append(self.note(text))
                continue
            fr=' '.join(instructions);key=plain_hebrew(' '.join(prayers))
            replacements={'המלך הקדוש':'האל הקדוש','המלך המשפט':'מלך אוהב צדקה ומשפט','השלום':'שלום'}
            woman='Une femme dit' in fr
            if woman and key=='מודה':replacements['מודה']='מודה'
            if key in replacements:
                match=find_hebrew(buffer,replacements[key])
                if match:
                    normal=buffer[match.start():match.end()];buffer=buffer[:match.start()]+buffer[match.end():];flush()
                    body='<p class="alternative-label">'+('Pour un homme' if woman else 'Formule habituelle')+'</p>'+self.prayer(normal)+'<p class="alternative-label">'+('Pour une femme' if woman else 'Pendant les dix jours de pénitence')+'</p>'+self.prayer(' '.join(prayers))
                    parts.append(self.box(body,'Choisir une seule formule',css='choice'))
                    continue
            flush()
            parts.append(self.conditional_items(items))
        flush()
        for text,target in after:parts.append(self.note(text,'Après ce passage',target,True))
        return ''.join(parts)

    def render(self):
        out=['<h2>'+html.escape(self.title)+'</h2>']
        i=0
        while i<len(self.records):
            r=self.records[i];p=r['plain'];items=self.items(r)
            if r['kind']=='heading':
                heading=self.c.heading(p)
                if heading.casefold()!=self.title.casefold():out.append('<h3>'+html.escape(heading)+'</h3>')
                i+=1;continue
            if self.is_meal and p=='אם המסובים שלושה או יותר אומרים':
                # Un seul contexte pour tout le dialogue, pas une condition par phrase.
                j=i+1
                while j<len(self.records) and not self.records[j]['plain'].startswith('ברוך אתה'):
                    j+=1
                body=[];self.in_zimoun=True
                try:
                    for part in self.records[i+1:j]:
                        sequence=self.items(part)
                        if sequence and all(k=='instruction' for k,_ in sequence):
                            fr=' '.join(t for _,t in sequence)
                            role={'Celui qui conduit le zimoun dit :':'Celui qui conduit',
                                  'Celui qui conduit le zimoun répond :':'Celui qui conduit',
                                  'Les convives répondent :':'Les convives'}.get(fr,fr)
                            body.append('<p class="role-label" id="p-'+str(part['i'])+'">'+html.escape(role)+'</p>')
                        else:body.append(self.record_body(part))
                finally:self.in_zimoun=False
                skip='<p class="card-rule"><a href="#p-'+str(j)+'">Sans zimoun : première bénédiction</a></p>'
                out.append('<div id="p-'+str(i)+'">'+self.box(skip+''.join(body),'Zimoun · trois convives ou plus','Dix convives ou plus : ajouter les mots entre crochets.',css='role')+'</div>')
                i=j;continue
            # Quelques intertitres de la source n'étaient pas balisés <big>.
            if self.is_amida and (p.startswith('קדושה') and len(p)<55 or p=='ברכת כהנים'):
                if p=='ברכת כהנים':
                    j=i+1
                    while j<len(self.records) and self.records[j]['kind']=='note':j+=1
                    nxt,text=self.next_prayer(j);body=''.join(self.record_body(x) for x in self.records[i+1:j])
                    out.append('<div id="p-'+str(i)+'">'+self.box(body,'Bénédiction des Cohanim · répétition de l’Amida',resume='Suite',href='#p-'+str(nxt) if nxt is not None else '',css='role')+'</div>');i=j;continue
                j=i+1
                while j<len(self.records) and self.records[j]['kind']=='note':j+=1
                nxt,text=self.next_prayer(j);body=''.join(self.record_body(x) for x in self.records[i+1:j])
                out.append('<div id="p-'+str(i)+'">'+self.box(body,'Kedoucha · répétition de l’Amida',resume='Suite',href='#p-'+str(nxt) if nxt is not None else '',css='role')+'</div>');i=j;continue
            if self.is_amida and p.startswith('כתר יתנו'):
                nxt,text=self.next_prayer(i+1);out.append('<div id="p-'+str(i)+'">'+self.box(self.paragraph(r),'Kedoucha de Moussaf · répétition',resume='Suite',href='#p-'+str(nxt) if nxt is not None else '',css='role')+'</div>');i+=1;continue
            if self.is_amida and (p=='מודים דרבנן' or p.startswith('מודים דרבנן בחזרת')):
                j=i+1
                if p=='מודים דרבנן':
                    while j<len(self.records) and self.records[j]['kind']=='note' and not self.records[j]['plain'].startswith('בחנוכה'):j+=1
                    body=''.join(self.record_body(x) for x in self.records[i+1:j])
                else:body=self.paragraph(r)
                nxt,text=self.next_prayer(j)
                out.append('<div id="p-'+str(i)+'">'+self.box(body,'Modim derabbanan · réponse de l’assemblée','Pendant la répétition, à l’ouverture de Modim par l’officiant.',resume='Suite',href='#p-'+str(nxt) if nxt is not None else '',css='role')+'</div>');i=j;continue
            # Barékhénou / Barékh alénou : deux versions d'une même bénédiction.
            if self.is_amida and p=='בקיץ' and i+3<len(self.records) and self.records[i+2]['plain']=='בחורף':
                body='<p class="alternative-label">En été</p>'+self.record_body(self.records[i+1])+'<p class="alternative-label">En hiver</p>'+self.record_body(self.records[i+3])
                nxt,text=self.next_prayer(i+4)
                out.append('<div id="p-'+str(i)+'">'+self.box(body,'Bénédiction de l’année · une seule version',resume='Suite',href='#p-'+str(nxt) if nxt is not None else '',css='choice')+'</div>');i+=4;continue
            if self.is_amida and p.startswith('בקיץ') and 'בחורף' in p and 'מוריד הטל' in p:
                body='';parts=self.items(r)
                for kind,text in parts:
                    body+=('<p class="alternative-label">'+html.escape(text)+'</p>') if kind=='instruction' else self.prayer(text)
                nxt,text=self.next_prayer(i+1)
                out.append('<div id="p-'+str(i)+'">'+self.box(body,'Choisir une seule formule',css='choice')+'</div>');i+=1;continue
            standalone=r['kind']=='note' and items and all(k=='instruction' for k,_ in items)
            if standalone and i+1<len(self.records) and self.records[i+1]['kind']=='note' and any(k=='prayer' for k,_ in self.items(self.records[i+1])):
                fr=' '.join(t for _,t in items)
                if _condition(fr) or self.is_amida and ('répétition' in fr or 'officiant' in fr):
                    j=i+2;first=self.records[i+1]['plain']
                    if re.match(r'אלהינו ואלהי אבותינו[, ]+יעלה',first) or first.startswith('על הנסים') or p.startswith('אם שכח') or p.startswith('בתענית ציבור השליח') or first.startswith('אבינו מלכנו'):
                        while j<len(self.records) and self.records[j]['kind']=='note':j+=1
                    nxt,text=self.next_prayer(j);body=''.join(self.record_body(x) for x in self.records[i+1:j])
                    if re.match(r'אלהינו ואלהי אבותינו[, ]+יעלה',first):
                        body=self.note('À « beyom », choisir la date, puis poursuivre à « Léra’hem bo… ».')+body
                    out.append('<div id="p-'+str(i)+'">'+self.box(body,_brief_rubric(fr),resume='Suite',href='#p-'+str(nxt) if nxt is not None else '')+'</div>');i=j;continue
            content='' if standalone else self.paragraph(r)
            if standalone:
                nxt,text=self.next_prayer(i+1)
                fr=' '.join(t for _,t in items)
                if _technical(fr):
                    marker=self.footnote(fr,'')
                    content='<p class="instruction">Précision sur ce passage '+marker+'</p>'
                elif re.match(r'^(?:Deux fois|Trois fois|Sept fois|Répéter|Jusqu’ici)',fr):
                    previous=next((x['text'] for x in reversed(self.records[:i]) if any(k=='prayer' for k,_ in self.items(x))), '')
                    content=self.note(fr,'Pour le passage ci-dessus',previous,True)
                else:content=self.note(fr,'Pendant le passage suivant' if re.search(r's’incliner|toucher|embrasser|passer les',fr) else 'Avant le passage suivant',text)
            out.append('<div id="p-'+str(i)+'">'+content+'</div>');i+=1
        if self.notes:
            out.append('<div class="endnotes"><h3>Explications liées aux repères numérotés</h3>')
            for n,text,target in self.notes:
                out.append('<p id="note-'+str(n)+'"><strong>['+str(n)+']</strong> '+('<em>À « '+html.escape(target)+' ».</em> ' if target else '')+html.escape(text)+' <a href="#appel-'+str(n)+'">Retour au texte</a></p>')
            out.append('</div>')
        return '\n'.join(out)

def render_section(title,paragraphs,mode,ref,consignes):
    return ReadingLayout(title,paragraphs,mode,ref,consignes).render()


