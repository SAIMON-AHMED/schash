%%
%% This is file `aucmcs.cls',
%====================================================================
%%% @LaTeX-file{
%%%   filename  = "aucmcs.cls",
%%%   version   = "2.0",
%%%   date      = "January 11, 2010",
%%%   author    = "Claudiu Ionut Popirlan",
%%%   copyright = "Copyright 2010, University of Craiova,
%%%                all rights reserved.  Copying of this file is
%%%                authorized only if either:
%%%                (1) you make absolutely no changes to your copy,
%%%                including name; OR
%%%                (2) if you do make changes, you first rename it
%%%                to some other name.",
%%%   address   = "University of Craiova
%%%                Department of Computer Science
%%%                Craiova, Dolj
%%%                Romania
%%%   FAX       = "",
%%%   email     = "ami.craiova@gmail.com",
%%%   codetable = "ISO/ASCII",
%%%   abstract  = "This is the document class for Annals of University of Craiova,
%%%                Mathematics and Computer Science series.
%%%                It is designed for use with LaTeX, and is closely
%%%                modeled on the amsart class."
%%% }
%%%
%====================================================================

\NeedsTeXFormat{LaTeX2e}% LaTeX 2.09 can't be used (nor non-LaTeX)
[1994/12/01]% LaTeX date must December 1994 or later
\ProvidesClass{aucmcs}[2003/06/06 v1.0]

\LoadClass[reqno,tbtags]{amsart}

\footskip=24pt
\textheight=210mm 
\topskip=10pt
\textwidth=130mm

\def\ps@headings{\ps@empty
  \def\@evenhead{%
    \setTrue{runhead}%
    \normalfont\scriptsize
    \rlap{\thepage}\hfil \leftmark{}{}\hfil
            \llap{\aurhfont \shortpublname}}%
  \def\@oddhead{%
    \setTrue{runhead}%
    \normalfont\scriptsize 
    \rlap{Vol.~\currentvolume, \currentyear}\hfil
    \rightmark{}{}\hfil \llap{\thepage}}%
  \let\@mkboth\markboth
}

\def\publname{Annals of the University of Craiova, Mathematics and Computer Science Series}

\def\@settitle{%
\begingroup        
  \baselineskip14\p@\relax
    \bfseries \noindent \Large \raggedright \sloppy
  \@title
\endgroup
}

\def\@setauthors{%
  \begingroup
  \raggedright
  \lefthyphenmin=99
  \trivlist
\@topsep30\p@\relax
  \advance\@topsep by -\baselineskip
  \item\relax
  \andify\authors
  \def\\{\protect\linebreak}%
{\scshape \authors}%
  \endtrivlist
  \endgroup
}

\renewenvironment{abstract}{%
  \ifx\maketitle\relax
    \ClassWarning{\@classname}{Abstract should precede
      \protect\maketitle\space in AMS documentclasses; reported}%
  \fi
  \global\setbox\abstractbox=\vtop \bgroup
    \normalfont\Small
    \list{}{\labelwidth\z@
      \leftmargin1pc \rightmargin\leftmargin
      \listparindent\normalparindent \itemindent\z@
      \parsep\z@ \@plus\p@
      \let\fullwidthdisplay\relax
    }%
    \item[\hskip\labelsep\scshape\abstractname.]%   
}{%
  \endlist\egroup
  \ifx\@setabstract\relax 
  \@setabstracta 
  \fi
}

\def\@secnumfont{\bfseries}
\def\section{\@startsection{section}{1}%
  \z@{\linespacing\@plus\linespacing}{\linespacing}%
  {\normalfont\bfseries}}
\def\subsection{\@startsection{subsection}{1}%
  \z@{.7\linespacing\@plus\linespacing}{-.5em}%
  {\normalfont\bfseries}}
\def\subsubsection{\@startsection{subsubsection}{1}%
  \z@{.5\linespacing\@plus.7\linespacing}{-.5em}%
  {\normalfont\itshape}}
\def\bibsection{\@startsection{section}{\@M}%
  \z@{.9\linespacing\@plus\linespacing}{.5\linespacing}%
  {\normalfont\scshape}}  
\renewenvironment{thebibliography}[1]{%
  \@xp\bibsection\@xp{\refname}%
  \normalfont\footnotesize\labelsep .5em\relax
  \renewcommand\theenumiv{\arabic{enumiv}}\let\p@enumiv\@empty
  \list{\@biblabel{\theenumiv}}{\settowidth\labelwidth{\@biblabel{#1}}%
    \leftmargin\labelwidth \advance\leftmargin\labelsep
    \usecounter{enumiv}}%
  \sloppy \clubpenalty\@M \widowpenalty\clubpenalty
  \sfcode`\.=\@m
  \raggedright  
}{%
  \def\@noitemerr{\@latex@warning{Empty `thebibliography' environment}}%
  \endlist
}
\def\footnoterule{\kern-.4\p@
        \hrule\@width \textwidth\kern11\p@\kern-\footnotesep}


\renewcommand{\datename}{Received}  

\def\@setaddresses{\par
  \nobreak \begingroup \raggedright
\footnotesize
  \def\author##1{\nobreak\addvspace\bigskipamount}%
  \def\\{\linebreak\indent\ignorespaces}%
  \interlinepenalty\@M
  \def\address##1##2{\begingroup
    \par\addvspace\bigskipamount\indent
    \@ifnotempty{##1}{(\ignorespaces##1\unskip) }%
    {\scshape\ignorespaces##2}\par\endgroup}%
  \def\curraddr##1##2{\begingroup
    \@ifnotempty{##2}{\nobreak\indent{\itshape Current address}%
      \@ifnotempty{##1}{, \ignorespaces##1\unskip}\/:\space
      ##2\par}\endgroup}%
  \def\email##1##2{\begingroup
    \@ifnotempty{##2}{\nobreak\indent{\itshape E-mail address}%
      \@ifnotempty{##1}{, \ignorespaces##1\unskip}\/:\space
      \ttfamily##2\par}\endgroup}%
  \def\urladdr##1##2{\begingroup
    \@ifnotempty{##2}{\nobreak\indent{\itshape URL}%
      \@ifnotempty{##1}{, \ignorespaces##1\unskip}\/:\space
      \ttfamily##2\par}\endgroup}%
  \addresses
  \endgroup
}

\def\@setsubjclass{
  \normalfont\Small
  {\itshape\subjclassname.}\enspace\@subjclass\@addpunct.}
\def\@setkeywords{%
  \normalfont\Small
  {\itshape \keywordsname.}\enspace \@keywords\@addpunct.}

  \def\@intref{intervmarker}

\def\@maketitle{%
  \normalfont\normalsize
  \let\@makefnmark\relax  \let\@thefnmark\relax
  
  \ifx\@empty\@date\else \@footnotetext{\@setdate}\fi
  
  \ifx\@empty\thankses\else \@footnotetext{%
    \def\par{\let\par\@par}\@setthanks}\fi
  \@mkboth{\@nx\shortauthors}{\@nx\shorttitle}%
  \global\topskip42\p@\relax % 5.5pc   "   "   "     "     "
  \@settitle
  \ifx\@empty\authors \else \@setauthors \fi
  \ifx\@empty\@dedicatory
  \else
    \baselineskip18\p@
    \vtop{\centering{\footnotesize\itshape\@dedicatory\@@par}%
      \global\dimen@i\prevdepth}\prevdepth\dimen@i
  \fi
  
  
  \ifx \@intmarker \@intref
  \else
  \addvspace\bigskipamount\footnoterule
  \fi
  
  \@setabstract
  
  \ifx\@empty\@keywords
  \else 
  \list{}{\labelwidth\z@
      \leftmargin1pc \rightmargin\leftmargin
      \listparindent\normalparindent \itemindent\z@
      \parsep\z@ \@plus\p@
      \let\fullwidthdisplay\relax\raggedright
    }%
    \item[] \@setsubjclass  
    \item[] \@setkeywords
    \linebreak
  \fi  
    
  \ifx \@intmarker \@intref
  \else
  \addvspace\bigskipamount\footnoterule
  \fi
  
  \normalsize
  \if@titlepage
    \newpage
  \else
    \dimen@34\p@ \advance\dimen@-\baselineskip
    \vskip\dimen@\relax
  \fi
} % end \@maketitle

\def\article@logo{%
  \set@logo{%
    \publname
    \newline\volinfo, \pageinfo
    \newline ISSN: \ISSN
  }%
}

\renewenvironment{thebibliography}[1]{%
  \@xp\section\@xp*\@xp{\refname}%
  \normalfont\footnotesize\labelsep .5em\relax
  \renewcommand\theenumiv{\arabic{enumiv}}\let\p@enumiv\@empty
  \list{\@biblabel{\theenumiv}}{\settowidth\labelwidth{\@biblabel{#1}}%
    \leftmargin\labelwidth \advance\leftmargin\labelsep
    \usecounter{enumiv}}%
  \sloppy \clubpenalty\@M \widowpenalty\clubpenalty
  \sfcode`\.=\@m
}{%
  \def\@noitemerr{\@latex@warning{Empty `thebibliography' environment}}%
  \endlist
}

\def\@setcopyright{%
}

\def\volinfo
{%
      Volume \currentvolume, \currentyear
}%
\def\volume#1{\def\currentvolume{#1}}
\def\year#1{\def\currentyear{#1}}
\def\issn#1{\def\ISSN{#1}}

\DeclareOption{intervention}
{
    \def\@intmarker{intervmarker}
}

\DeclareOption{french}
{
\newtheorem{theorem}{Th\'eor\`eme}[section]
\newtheorem{lemma}{Lemme}[section]
\newtheorem{proposition}{Proposition}[section]
\newtheorem{conjecture}{Conjecture}[section]
\newtheorem{example}{Exemple}[section]
\newtheorem{definition}{D\'{e}finition}[section]
\newtheorem{corollary}{Corollaire}[section]
\newtheorem{remark}{Remarque}[section]

\def\keywordsname{Mots clef et phrases}

\@namedef{subjclassname@2010}{%
  Classification AMS 2010 des sujets}
  
\renewcommand{\andify}{%
  \nxandlist{\unskip, }{\unskip{} et~}{\unskip{} et~}}
\def\and{\unskip{ }et \ignorespaces}  

\renewcommand{\datename}{\textit{Re\c{c}u}:}
}

\DeclareOption{english}
{
\newtheorem{theorem}{Theorem}[section]
\newtheorem{lemma}{Lemma}[section]
\newtheorem{proposition}{Proposition}[section]
\newtheorem{conjecture}{Conjecture}[section]
\newtheorem{example}{Example}[section]
\newtheorem{definition}{Definition}[section]
\newtheorem{corollary}{Corollary}[section]
\newtheorem{remark}{Remark}[section]

\def\keywordsname{Key words and phrases}

\@namedef{subjclassname@2010}{%
  2010 Mathematics Subject Classification}

\renewcommand{\andify}{%
  \nxandlist{\unskip, }{\unskip{} and~}{\unskip, and~}}
\def\and{\unskip{ }and \ignorespaces}

\renewcommand{\datename}{Received}
}

\ProcessOptions

\endinput
%%
%% End of file `aucmcs.cls'.
