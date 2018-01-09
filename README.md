# RTM git repository
------------------------------

Repository for RTM developmentde-CLM-ification of ED. Contains a full copy of RTM
from recent svn trunk tags. 

## Repository structure
-----------------------

Branches
  * master : main RTM release branch
  * rtm-svn : rtm trunk tags from CESM svn
  * cesm2git : tools for pulling svn branch tags into git

# CLM

Note on tag count. Running :

.. code-block::

    git tag | wc
         509     509    6108
    
    svn ls https://svn-ccsm-models.cgd.ucar.edu/clm2/trunk_tags | wc
         511     511    6638
     
There are two fewer tags in git. Diffing the results:

.. code-block::

    diff tag-list-clm-svn.txt tag-list-clm-git.txt 
    207d206
    < clm4_0_5
    511d509
    < clm4_6_00

`clm4_0_5` was a typo, it is really `clm4_5_57`.

`clm4_6_00` was retagged as `clm4_5_1_r076`

# CISM

.. code-block::

    git tag | wc
         149     149    1813
         
    svn ls https://svn-ccsm-models.cgd.ucar.edu/glc/trunk_tags | wc
         150     150    1977
     
`cism1_100525a` had no diffs with `cism1_100525`

# MOSART

.. code-block::

    git tag | wc
          28      28     364
    
    svn ls https://svn-ccsm-models.cgd.ucar.edu/mosart/trunk_tags | wc
          29      29     406
      

`mosart1_0_14` and `mosart1_0_15` are the same

# RTM
    
.. code-block::
    
     git tag | wc
          63      63     630
     svn ls https://svn-ccsm-models.cgd.ucar.edu/rivrtm/trunk_tags | wc
          63      63     693
      

# PTCLM

.. code-block::

     git tag | wc
          40      40     566
     svn ls https://svn-ccsm-models.cgd.ucar.edu/PTCLM/trunk_tags | wc
          41      41     622
          
`PTCLM2_171016b` is the same as `PTCLM2_171016`
