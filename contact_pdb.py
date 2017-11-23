#!/usr/bin/env python
# 2016-01-28 Chengxin Zhang
docstring='''
contact_pdb.py [options] pdb.pdb
    Calculate residue contacts in single chain PDB file "pdb.pdb"

Options:
    -cutoff=8  distance cutoff (in Angstrom) for contact, usu between 6 and 12

    -atom={CA,CB} calculate distance between "CA" for all residues, or "CA" for 
        gly and "CB" for other 19 amino acids

    -outfmt={list,dist,plot} output format:
        "list": tab-eliminated list listing residue index for contact pairs
        "dist": tab-eliminated list listing residue distances for all pairs
        "stat": statistics on number of contacts at short/medm/long/all
                range and protein length L

    -range={all,short,medium,long} sequences seperation range x
        "all":     1<=x
        "short":   6<=x<12
        "medium": 12<=x<24
        "long":   24<=x   (most useful)
        (default): 6<=x


contact_pdb.py [options] pdb.pdb contact.map
    Calculate accuracy of residue contacts map "contact.map" according to
    in single chain PDB file "pdb.pdb"

    "contact.map" could be of NN-BAYES contact map format (resi1 resi2 p)
    or CASP Residue-Residue Separation Distance Prediction Format
    (resi1 resi2 dist_lower dist_upper p). See 
    http://predictioncenter.org/casproll/index.cgi?page=format#RR

Options:
    -cutoff=8

    -atom={CB,CA} atom with which contact is considered.
        CB - CA for GLY, CB for other 19 AA
        CA - CA for all 20 AA

    -range={all,short,medium,long}

    -outfmt={list,dist,stat} output format:
        "list": list showing if predicted contact pairs are TRUE
                #resi1 resi2 dist TRUE/FALSE p
        "dist": the same as above but actual distance is also reported
                #resi1 resi2 dist TRUE/FALSE p
        "stat": statistics on accuracy (ACC): (short2 stands for short range
                contact ACC for top L/2, L=protein length)
                #short1 short2 short5 medm1 medm2 medm5 long1 long2 long5
                    all1 all2 all5

    -cutoff_all=0      # ignore contact prediction p<=0
    -cutoff_short=0.5  # ignore short  range contact prediction p<=0.5
    -cutoff_medium=0.4 # ignore medium range contact prediction p<=0.4
    -cutoff_long=0.3   # ignore medium range contact prediction p<=0.3

    -offset=0    add "offset" to residue index in predicted contact map
    -infmt={rr,gremlin} input format of contact map
        rr - CASP RR, NeBcon, or mfDCA format
        gremlin - matrix of confidence score
'''
import sys,os
import re

# see http://predictioncenter.org/casp12/doc/rr_help.html for contact range
# defination. Note that NeBcon/NN-BAYES uses different defination for long
# range contact
short_range_def=6 # short_range_def <= separation < medm_range_def
medm_range_def=12 # medm_range_def  <= separation < long_range_def
long_range_def=24 # long_range_def  <= separation. 25 in NeBcon/NN-BAYES

def read_contact_map(infile="contact.map",
    cutoff_all=0,cutoff_short=0,cutoff_medium=0,cutoff_long=0,
    sep_range=str(short_range_def),offset=0,infmt="rr"):
    '''Read NN-BAYES or CASP RR format contact map. return them in a zipped 
    list with 3 fields for each residue pair. 1st field & 2nd filed are for 
    residue indices, and 3rd field is for euclidean distance.
    '''
    resi1=[] # residue index 1 list
    resi2=[] # residue index 2 list
    p=[] # cscore of contact prediction accuracy list
    fp=open(infile,'rU')
    lines=fp.read().strip().splitlines()
    fp.close()
    pattern=re.compile('(^\d+\s+\d+\s+\d+\s+\d+\s+[-+.e\d]+)|(^\d+\s+\d+\s+[-+.e\d]+)|(^\d+\s+[A-Z]\s+\d+\s+[A-Z]\s+[-+.e\d]+\s+[-+.e\d]+)')
    if infmt!="rr":
        for i,line in enumerate(lines):
            for j,cscore in enumerate(line.split()):
                if (j<=i):
                    continue
                seperation=abs(i-j)
                if (sep_range=="short"  and not \
                    short_range_def<=seperation<medm_range_def) or \
                   (sep_range=="medium" and not \
                    medm_range_def<=seperation<long_range_def) or \
                   (sep_range=="long"   and not long_range_def<=seperation):
                    continue
                elif not sep_range in ["all","short","medium","long"] \
                    and seperation<int(sep_range):
                    continue
                resi1.append(i+1)
                resi2.append(j+1)
                p.append(float(cscore))
        return zip(resi1,resi2,p)

    for line in lines:
        if not line.strip(): # skip empty lines
            continue
        match_list=pattern.findall(line.strip())
        if not match_list:
            continue
        line=[line for line in match_list[0] if line.strip()][0].split()
        if len(line)==6:
            line=[line[0],line[2],line[5]]
        if not len(line) in (3,5):
            continue

        resi_idx1=int(line[0])+offset # residue index 1
        resi_idx2=int(line[1])+offset # residue index 2
        cscore=float(line[-1]) # cscore for contact prediction
        seperation=abs(resi_idx1-resi_idx2)

        if (sep_range=="short"  and not \
            short_range_def<=seperation<medm_range_def) or \
           (sep_range=="medium" and not \
            medm_range_def<=seperation<long_range_def) or \
           (sep_range=="long"   and not long_range_def<=seperation):
            continue
        elif not sep_range in ["all","short","medium","long"] \
            and seperation<int(sep_range):
            continue

        if cscore<=cutoff_all or \
          (cscore<=cutoff_short  and seperation<=medm_range_def) or \
          (cscore<=cutoff_medium and medm_range_def<=seperation<long_range_def
          ) or (cscore<=cutoff_long and long_range_def<=seperation):
            continue

        resi1.append(resi_idx1)
        resi2.append(resi_idx2)
        p.append(cscore)
    return zip(resi1,resi2,p)

def calc_res_dist(infile="pdb.pdb",atom_sele="CA"):
    '''Calculate Residue Distances of the first chain in PDB file "infile",
    and return them in a zipped list with 3 fields for each element. 1st field
    & 2nd filed are for residue indices, 3rd field is for euclidean distance.
    
    atom_sele - select atoms whose euclidean distances are to be calculated
        "CA" for alpha carbon
        "CB" for alpha carbon in gly in beta carbon in all other amino acids'''
    fp=open(infile,'rU')
    struct=fp.read().split("ENDMDL")[0] # first model only
    fp.close()

    '''
     1 -  6  Record name  "ATOM  "
     7 - 11  Integer      serial     Atom  serial number.
    13 - 16  Atom         name       Atom name.
    17       Character    altLoc     Alternate location indicator.
    18 - 20  Residue name resName    Residue name.
    22       Character    chainID    Chain identifier.
    23 - 26  Integer      resSeq     Residue sequence number.
    27       AChar        iCode      Code for insertion of residues.
    31 - 38  Real(8.3)    x          Orthogonal coordinates for X 
    39 - 46  Real(8.3)    y          Orthogonal coordinates for Y
    47 - 54  Real(8.3)    z          Orthogonal coordinates for Z
    55 - 60  Real(6.2)    occupancy  Occupancy.
    61 - 66  Real(6.2)    tempFactor Temperature  factor.
    77 - 78  LString(2)   element    Element symbol, right-justified.
    79 - 80  LString(2)   charge     Charge  on the atom.
    '''
    model=[r for r in struct.splitlines() if r.startswith("ATOM  ")]
    chain_id=[r[21] for r in model][0] # first chain
    chain=dict()
    for r in model:
        if r[21]!=chain_id:
            continue # first chain
        resName=r[17:20] 
        resSeq=int(r[22:26])
        name=r[12:16].strip()
        x=float(r[30:38])
        y=float(r[38:46])
        z=float(r[46:54])
        if name==atom_sele or \
            (name=="CA" and not resSeq in chain): # CA if atom_sele is absent
            chain[resSeq]=(x,y,z)
    residues=sorted([k for k in chain]) # sorted list of residue index

    resi1=[] # residue index 1
    resi2=[] # residue index 2
    dist=[]  # euclidean distance, in Angstrom
    for i in range(len(residues)-1):
        idx1=residues[i]
        x1,y1,z1=chain[idx1]
        for j in range(i+1,len(residues)):
            idx2=residues[j]
            x2,y2,z2=chain[idx2]
            dx=x1-x2
            dy=y1-y2
            dz=z1-z2

            resi1.append(idx1)
            resi2.append(idx2)
            dist.append( (dx*dx+dy*dy+dz*dz)**.5)
            #dist.append( ((x1-x2)**2+(y1-y2)**2+(z1-z2)**2)**.5)
    return zip(resi1,resi2,dist)

def compare_res_contact(res_dist_list,res_pred_list,cutoff=8):
    '''compare residue contact map "res_dist_list" calculate from pdb to 
    predicted residue contact "res_pred_list. return the result in a zipped 
    list with 5 fields for each pair. 1st field & 2nd filed are for residue  
    indices, 3rd field is for euclidean distance, 4th field for contact prediction 
    confidence p. 5th field for whether they are in contact in PDB structure. 
    '''
    res_dist_dict=dict() # key is residue pair, value is distance
    for i,j,dist in res_dist_list:
        res_dist_dict[(i,j)]=dist
    res_pred_dict=dict() # key is residue pair, value is cscore
    for i,j,cscore in res_pred_list:
        res_pred_dict[(i,j)]=cscore

    cmp_list=[]
    for i,j in set(res_dist_dict.keys()).intersection(res_pred_dict.keys()):
        dist=res_dist_dict[(i,j)]
        cscore=res_pred_dict[(i,j)]
        cmp_list.append((cscore,i,j,dist,str(dist<cutoff).upper()))
   
    #if len(cmp_list)==0:
        #return []

    # sort on cscore
    p,resi1,resi2,dist,contact=map(list,zip(*sorted(cmp_list,reverse=True)))
    cmp_list=zip(resi1,resi2,dist,contact,p)
    return cmp_list

def calc_acc_contact(cmp_list,L,sep_range=str(short_range_def)):
    '''Calculate residue contact accuracy using ouput if "compare_res_contact"
    and length of protein 'L" '''
    top_pred=dict() # top L, L/2, L/5 prediction
    
    if not sep_range in ["medium","long"]:
        top_pred["short1"]=[res_pair for res_pair in cmp_list if \
            short_range_def<=abs(res_pair[0]-res_pair[1])<medm_range_def][:L]
        top_pred["short2"]=top_pred["short1"][:int(L/2)]
        top_pred["short5"]=top_pred["short1"][:int(L/5)]

    if not sep_range in ["short","long"]:
        top_pred["medm1" ]=[res_pair for res_pair in cmp_list if \
            medm_range_def<=abs(res_pair[0]-res_pair[1])<long_range_def][:L]
        top_pred["medm2" ]=top_pred["medm1" ][:int(L/2)]
        top_pred["medm5" ]=top_pred["medm1" ][:int(L/5)]

    if not sep_range in ["short","medium"]:
        top_pred["long1" ]=[res_pair for res_pair in cmp_list if \
            long_range_def<=abs(res_pair[0]-res_pair[1])][:L]
        top_pred["long2" ]=top_pred["long1" ][:int(L/2)]
        top_pred["long5" ]=top_pred["long1" ][:int(L/5)]

    if not sep_range in ["short","medium","long"]:
        top_pred["all1"  ]=cmp_list[:L]
        top_pred["all2"  ]=top_pred["all1"  ][:int(L/2)]
        top_pred["all5"  ]=top_pred["all1"  ][:int(L/5)]

    ACC=dict() # accuracy
    for key in top_pred:
        if top_pred[key]:
            ACC[key]=1.*len([e for e in top_pred[key] if e[3]=="TRUE"]
                )/int(L/float(key.lstrip("shortmedmlongall")))
                #)/len(top_pred[key])
        else:
            ACC[key]=0 # error
    return ACC,top_pred

def calc_contact_num(res_con_list,L):
    ''' calculate the number of contacts at different range '''
    con_num_dict={"short":0,"medm":0,"long":0,"all":len(res_con_list),"L":L}
    for resi1,resi2,dist in res_con_list:
        con_num_dict["short"]+=(
            short_range_def<=abs(resi2-resi1)<medm_range_def)
        con_num_dict["medm"]+=(
            medm_range_def<=abs(resi2-resi1)<long_range_def)
        con_num_dict["long"]+=(
            long_range_def<=abs(resi2-resi1))
    return con_num_dict

def calc_res_contact(res_dist_list,sep_range=str(short_range_def),cutoff=8):
    '''Calculate residue contacts from "res_dist_list", a zipped list of residue
    pair distances returned by calc_res_dist
    
    cutoff - distance cutoff (in Angstrom) for contact, usu between 6 and 12

    sep_range - range of sequence seperations x
        "all":    1<=x
        "short":  short_range_def <= x < medm_range_def
        "medium": medm_range_def  <= x < long_range_def
        "long":   long_range_def  <=x   (most useful)
        (default): short_range_def<=x'''
    res_dist_list_con=res_dist_list
    cutoff=float(cutoff)
    if cutoff:
        res_dist_list_con=[e for e in res_dist_list if e[2]<cutoff]

    if sep_range=="all":
        return [e for e in res_dist_list_con if 1<=abs(e[0]-e[1])]
    elif sep_range=="short":
        return [e for e in res_dist_list_con if \
            short_range_def<=abs(e[0]-e[1])<medm_range_def]
    elif sep_range=="medium":
        return [e for e in res_dist_list_con if \
            medm_range_def<=abs(e[0]-e[1])<long_range_def]
    elif sep_range=="long":
        return [e for e in res_dist_list_con if long_range_def<=abs(e[0]-e[1])]
    else:
        return [e for e in res_dist_list_con if int(sep_range)<=abs(e[0]-e[1])]

if __name__=="__main__":
    if len(sys.argv)<2:
        sys.stderr.write(docstring)
        exit()

    atom_sele="CB"
    cutoff=8
    outfmt="list"
    sep_range=str(short_range_def) # "6"
    cutoff_all   =0
    cutoff_short =0
    cutoff_medium=0
    cutoff_long  =0
    offset  =0
    infmt="rr"
    for arg in sys.argv[1:]:
        if arg.startswith("-cutoff="):
            cutoff=float(arg[len("-cutoff="):])
        elif arg.startswith("-atom="):
            atom_sele=arg[len("-atom="):]
        elif arg.startswith("-range="):
            sep_range=arg[len("-range="):]
            if sep_range=="medm":
                sep_range="medium"
        elif arg.startswith("-outfmt="):
            outfmt=arg[len("-outfmt="):]
        elif arg.startswith("-infmt="):
            infmt=arg[len("-infmt="):]
        elif arg.startswith("-cutoff_all="):
            cutoff_all=float(arg[len("-cutoff_all="):])
        elif arg.startswith("-cutoff_short="):
            cutoff_short=float(arg[len("-cutoff_short="):])
        elif arg.startswith("-cutoff_medium="):
            cutoff_medium=float(arg[len("-cutoff_medium="):])
        elif arg.startswith("-cutoff_long="):
            cutoff_long=float(arg[len("-cutoff_long="):])
        elif arg.startswith("-offset="):
            offset=int(arg[len("-offset="):])
        elif arg.startswith("-"):
            sys.stderr.write("ERROR! Unknown argument %s\n"%arg)
            exit()
    file_list=[arg for arg in sys.argv[1:] if not arg.startswith("-")]
    if not file_list:
        sys.stderr.write(docstring+"\nERROR! No PDB file")
        exit()
    
    res_dist_list=calc_res_dist(file_list[0],atom_sele)
    res_con_list=calc_res_contact(res_dist_list,sep_range,cutoff)

    L=map(list,zip(*res_dist_list))
    L=L[0]+L[1]
    L=max(L)-min(L)+1

    if len(file_list)==1: # calculate residue contact
        for res_pair in res_con_list:
            if outfmt.startswith("dist"):
                sys.stdout.write("%d\t%d\t%.1f\n"%(res_pair[0],res_pair[1],res_pair[2]))
            elif outfmt=="list":
                sys.stdout.write("%d\t%d\n"%(res_pair[0],res_pair[1]))
        if outfmt=="stat":
            con_num_dict=calc_contact_num(res_con_list,L)
            key_list=["short","medm","long","all","L"]
            sys.stderr.write('\t'.join(key_list)+'\n')
            sys.stdout.write('\t'.join([str(con_num_dict[key]
                ) for key in key_list])+'\n')
            
        if not cutoff and outfmt=="list":
            sys.stderr.write("\nWARNING! cutoff not set\n\n")


    elif len(file_list)==2: # calculate contact prediction accuracy
        res_pred_list=read_contact_map(file_list[1],
            cutoff_all,cutoff_short,cutoff_medium,cutoff_long,
            sep_range,offset,infmt)
        cmp_list=compare_res_contact(res_dist_list,res_pred_list,cutoff)

        if not outfmt.startswith("stat"):
            for res_pair in cmp_list: #resi1,resi2,dist,contact,p
                if outfmt.startswith("dist"):
                    sys.stdout.write("%d\t%d\t%.1f\t%s\t%.3f\n"%(res_pair[0],
                        res_pair[1],res_pair[2],res_pair[3],res_pair[4]))
                elif outfmt=="list":
                    sys.stdout.write("%d\t%d\t%s\t%.3f\n"%(res_pair[0],
                        res_pair[1],res_pair[3],res_pair[4]))
        else: # outfmt=="stat"
            ACC,top_pred=calc_acc_contact(cmp_list,L,sep_range)
            if sep_range == "short":
                key_list=["short1","short2","short5"]
            elif sep_range == "medium":
                key_list=["medm1" ,"medm2" ,"medm5"]
            elif sep_range == "long":
                key_list=["long1" ,"long2" ,"long5"]
            else:
                key_list=["short1","short2","short5",
                          "medm1" ,"medm2" ,"medm5",
                          "long1" ,"long2" ,"long5",
                          "all1"  ,"all2"  ,"all5"]
            sys.stderr.write('\t'.join(key_list)+'\n')
            sys.stdout.write('\t'.join(['%.3f'%ACC[key] for key in key_list]
                )+'\n')

        if not cutoff:
            sys.stderr.write("\nWARNING! cutoff not set\n\n")


    else:
        sys.stderr,write(docstring+"ERROR! Too many arguments.\n")
