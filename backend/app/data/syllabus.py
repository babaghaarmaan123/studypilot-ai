"""Syllabus templates.

When a student adds a subject we seed a realistic unit/topic breakdown so the
planner has something to schedule from day one. Students can edit, add or
delete anything afterwards — these are starting points, not gospel.

Shape:  {unit name: [(topic name, estimated_hours, difficulty 1-5), ...]}
Lookup order: "<curriculum>:<subject>"  ->  "<subject>"  ->  generic fallback.
"""

from typing import Dict, List, Tuple

Topic = Tuple[str, float, int]
UnitMap = Dict[str, List[Topic]]


_MATHS_A_LEVEL: UnitMap = {
    "Pure Mathematics 1": [
        ("Algebraic expressions and surds", 3, 2),
        ("Quadratics and the discriminant", 3, 2),
        ("Equations and inequalities", 3, 2),
        ("Graphs and transformations", 3, 3),
        ("Straight line graphs", 2.5, 2),
        ("Circles", 3, 3),
        ("Binomial expansion", 3, 3),
        ("Trigonometric ratios and identities", 4, 3),
        ("Differentiation from first principles", 4, 3),
        ("Applications of differentiation", 4, 4),
        ("Integration and areas under curves", 4, 3),
        ("Exponentials and logarithms", 3.5, 3),
    ],
    "Pure Mathematics 2": [
        ("Algebraic methods and proof", 3, 3),
        ("Functions and inverse functions", 3, 3),
        ("Sequences and series", 4, 3),
        ("Radians and small angle approximations", 3, 3),
        ("Trigonometric functions and identities", 4, 4),
        ("Parametric equations", 3.5, 4),
        ("Differentiation: chain, product, quotient", 4.5, 4),
        ("Integration by substitution and parts", 5, 5),
        ("Numerical methods", 3, 3),
        ("Vectors in three dimensions", 3.5, 3),
    ],
    "Statistics": [
        ("Data collection and sampling", 2, 2),
        ("Measures of location and spread", 2.5, 2),
        ("Representations of data", 2.5, 2),
        ("Correlation and regression", 3, 3),
        ("Probability and Venn diagrams", 3, 3),
        ("Binomial distribution", 3, 3),
        ("Normal distribution", 3.5, 4),
        ("Hypothesis testing", 4, 4),
    ],
    "Mechanics": [
        ("Modelling in mechanics and units", 2, 2),
        ("Constant acceleration (SUVAT)", 3, 2),
        ("Forces and Newton's laws", 4, 3),
        ("Variable acceleration and calculus", 3.5, 4),
        ("Moments", 3, 3),
        ("Projectiles", 3.5, 4),
        ("Friction and inclined planes", 3.5, 4),
    ],
}

_PHYSICS_A_LEVEL: UnitMap = {
    "Measurements and Errors": [
        ("SI units and derived quantities", 1.5, 1),
        ("Uncertainty and error propagation", 2.5, 3),
        ("Practical skills and graph analysis", 2.5, 2),
    ],
    "Mechanics and Materials": [
        ("Scalars, vectors and resolving forces", 2.5, 2),
        ("Moments and equilibrium", 2.5, 3),
        ("Motion graphs and equations", 3, 2),
        ("Projectile motion", 3, 3),
        ("Newton's laws and momentum", 4, 3),
        ("Work, energy and power", 3, 3),
        ("Materials: Hooke's law and Young modulus", 3.5, 3),
    ],
    "Electricity": [
        ("Current, charge and potential difference", 2.5, 2),
        ("Resistivity and I–V characteristics", 3, 3),
        ("Series and parallel circuits", 3, 3),
        ("EMF and internal resistance", 3, 3),
        ("Potential dividers", 2.5, 3),
    ],
    "Waves and Optics": [
        ("Progressive and stationary waves", 3, 3),
        ("Superposition and interference", 3.5, 4),
        ("Diffraction gratings", 3, 4),
        ("Refraction and total internal reflection", 3, 3),
    ],
    "Further Mechanics and Fields": [
        ("Circular motion", 3, 4),
        ("Simple harmonic motion", 4, 4),
        ("Gravitational fields", 3.5, 4),
        ("Electric fields and capacitance", 4, 4),
        ("Magnetic fields and induction", 4.5, 5),
    ],
    "Nuclear and Thermal Physics": [
        ("Thermal energy and specific heat capacity", 3, 3),
        ("Ideal gases and kinetic theory", 3.5, 4),
        ("Radioactive decay and half-life", 3.5, 3),
        ("Nuclear energy: fission and fusion", 3, 4),
    ],
}

_CHEMISTRY_A_LEVEL: UnitMap = {
    "Physical Chemistry": [
        ("Atomic structure and mass spectrometry", 3, 2),
        ("Amount of substance and moles", 3.5, 3),
        ("Bonding and structure", 3.5, 3),
        ("Energetics and Hess's law", 3.5, 3),
        ("Kinetics and rate equations", 4, 4),
        ("Chemical equilibria and Kc", 4, 4),
        ("Redox and electrode potentials", 4, 4),
        ("Acids, bases and pH calculations", 4.5, 5),
        ("Thermodynamics and entropy", 4, 5),
    ],
    "Inorganic Chemistry": [
        ("Periodicity", 2.5, 2),
        ("Group 2 alkaline earth metals", 2.5, 2),
        ("Group 7 halogens", 2.5, 2),
        ("Period 3 elements and oxides", 3, 3),
        ("Transition metals and complex ions", 4.5, 5),
    ],
    "Organic Chemistry": [
        ("Nomenclature and isomerism", 3, 2),
        ("Alkanes and alkenes", 3, 2),
        ("Haloalkanes and reaction mechanisms", 3.5, 3),
        ("Alcohols and carbonyls", 3.5, 3),
        ("Carboxylic acids and esters", 3.5, 3),
        ("Aromatic chemistry", 4, 4),
        ("Amines, amino acids and polymers", 4, 4),
        ("Organic synthesis and analysis", 4, 5),
        ("NMR and spectroscopy", 4, 4),
    ],
}

_BIOLOGY_A_LEVEL: UnitMap = {
    "Biological Molecules": [
        ("Carbohydrates and lipids", 3, 2),
        ("Proteins and enzymes", 3.5, 3),
        ("Nucleic acids and DNA replication", 3.5, 3),
        ("Water and inorganic ions", 2, 2),
    ],
    "Cells": [
        ("Cell structure and microscopy", 3, 2),
        ("Cell membranes and transport", 3.5, 3),
        ("Cell division and the cell cycle", 3, 3),
        ("Immunology", 3.5, 3),
    ],
    "Organisms Exchange Substances": [
        ("Gas exchange systems", 3, 2),
        ("Digestion and absorption", 3, 2),
        ("Mass transport in animals", 3.5, 3),
        ("Mass transport in plants", 3, 3),
    ],
    "Genetics and Variation": [
        ("DNA, genes and chromosomes", 3, 3),
        ("Protein synthesis", 3.5, 4),
        ("Genetic diversity and mutation", 3, 3),
        ("Biodiversity and classification", 3, 2),
    ],
    "Energy Transfers": [
        ("Photosynthesis", 4, 4),
        ("Respiration", 4, 4),
        ("Energy and nutrient cycles", 3, 3),
    ],
    "Response, Genetics and Ecosystems": [
        ("Nervous coordination and synapses", 4, 4),
        ("Muscles and homeostasis", 4, 4),
        ("Inheritance and population genetics", 4.5, 5),
        ("Populations and ecosystems", 3.5, 3),
        ("Gene expression and biotechnology", 4.5, 5),
    ],
}

_COMPUTER_SCIENCE: UnitMap = {
    "Fundamentals of Programming": [
        ("Data types, variables and operators", 2.5, 2),
        ("Selection, iteration and subroutines", 3, 2),
        ("Arrays, records and file handling", 3, 3),
        ("Object-oriented programming", 4, 4),
        ("Recursion", 3, 4),
    ],
    "Data Structures and Algorithms": [
        ("Stacks, queues and linked lists", 3.5, 3),
        ("Trees, graphs and hash tables", 4, 4),
        ("Searching algorithms", 3, 3),
        ("Sorting algorithms and complexity", 4, 4),
        ("Dijkstra's and A* pathfinding", 4, 5),
        ("Big-O notation", 3, 4),
    ],
    "Computer Systems": [
        ("Number systems and binary arithmetic", 3, 2),
        ("Boolean algebra and logic gates", 3, 3),
        ("Processor architecture and fetch-execute", 3.5, 3),
        ("Assembly language and addressing modes", 3.5, 4),
        ("Operating systems and memory management", 3, 3),
    ],
    "Networks and Databases": [
        ("Network topologies and protocols", 3, 3),
        ("TCP/IP stack and packet switching", 3, 3),
        ("Relational databases and normalisation", 3.5, 3),
        ("SQL queries", 3, 3),
        ("Security, encryption and hashing", 3, 3),
    ],
    "Theory and Impact": [
        ("Finite state machines and regular expressions", 3.5, 4),
        ("Turing machines and computability", 3.5, 5),
        ("Ethical, legal and environmental issues", 2.5, 2),
        ("Non-exam assessment project", 12, 4),
    ],
}

_ECONOMICS: UnitMap = {
    "Microeconomics": [
        ("Scarcity, choice and the PPF", 2, 2),
        ("Demand, supply and elasticities", 3.5, 3),
        ("Market failure and externalities", 3.5, 3),
        ("Government intervention", 3, 3),
        ("Costs, revenues and profit", 3.5, 3),
        ("Market structures", 4, 4),
        ("Labour markets", 3, 4),
        ("Income and wealth inequality", 2.5, 3),
    ],
    "Macroeconomics": [
        ("Measures of economic performance", 3, 2),
        ("Aggregate demand and supply", 3.5, 3),
        ("Economic growth and the cycle", 3, 3),
        ("Inflation and unemployment", 3.5, 3),
        ("Fiscal and monetary policy", 4, 4),
        ("International trade and exchange rates", 4, 4),
        ("Development economics", 3, 3),
    ],
    "Exam Technique": [
        ("25-mark essay structure and evaluation", 4, 4),
        ("Data response technique", 3, 3),
        ("Diagram accuracy drill", 2.5, 2),
    ],
}

_BUSINESS: UnitMap = {
    "Marketing and People": [
        ("Meeting customer needs and market research", 3, 2),
        ("The marketing mix and strategy", 3, 2),
        ("Managing people and motivation theory", 3.5, 3),
        ("Organisational design and leadership", 3, 3),
    ],
    "Operations and Finance": [
        ("Operational performance and efficiency", 3, 3),
        ("Quality, inventory and supply chain", 3, 3),
        ("Sources of finance", 3, 2),
        ("Break-even and cash flow forecasting", 3.5, 3),
        ("Ratio and financial statement analysis", 4, 4),
    ],
    "Strategy": [
        ("Business objectives and strategic direction", 3, 3),
        ("Ansoff, Porter and portfolio analysis", 3.5, 4),
        ("Growth, globalisation and multinationals", 3.5, 3),
        ("Managing change and decision trees", 3.5, 4),
    ],
}

_PSYCHOLOGY: UnitMap = {
    "Approaches and Research Methods": [
        ("Behaviourist and social learning approaches", 3, 3),
        ("Cognitive and biological approaches", 3, 3),
        ("Psychodynamic and humanistic approaches", 3, 3),
        ("Experimental design and sampling", 3.5, 3),
        ("Data handling and inferential statistics", 4, 4),
    ],
    "Core Topics": [
        ("Memory: models and eyewitness testimony", 3.5, 3),
        ("Attachment", 3, 3),
        ("Social influence and conformity", 3, 2),
        ("Psychopathology", 3.5, 3),
    ],
    "Options": [
        ("Biopsychology", 3.5, 4),
        ("Issues and debates", 3.5, 4),
        ("Schizophrenia", 4, 4),
        ("Forensic psychology", 3.5, 3),
    ],
}

_ENGLISH_LIT: UnitMap = {
    "Set Texts": [
        ("Close reading of the drama text", 4, 3),
        ("Close reading of the prose text", 4, 3),
        ("Poetry anthology analysis", 4.5, 4),
        ("Unseen poetry technique", 3.5, 4),
    ],
    "Context and Criticism": [
        ("Historical and social context", 3, 3),
        ("Critical readings and theory", 3.5, 4),
        ("Comparative essay planning", 3.5, 4),
    ],
    "Assessment": [
        ("Quotation bank and memorisation", 4, 3),
        ("Timed essay practice", 4, 4),
        ("Non-exam assessment coursework", 8, 3),
    ],
}

_ENGLISH_LANG: UnitMap = {
    "Language Analysis": [
        ("Lexis, semantics and grammar frameworks", 3.5, 3),
        ("Phonetics and phonology", 3, 3),
        ("Pragmatics and discourse", 3, 3),
    ],
    "Language in Context": [
        ("Language and gender", 3, 3),
        ("Language and occupation", 3, 3),
        ("Language change over time", 3.5, 3),
        ("Child language acquisition", 3.5, 3),
    ],
    "Writing Skills": [
        ("Directed writing technique", 3, 3),
        ("Comparative analysis essays", 3.5, 4),
        ("Timed exam practice", 4, 4),
    ],
}

_HISTORY: UnitMap = {
    "Breadth Study": [
        ("Political developments and key figures", 4, 3),
        ("Economic and social change", 4, 3),
        ("Continuity and change over the period", 3.5, 4),
    ],
    "Depth Study": [
        ("Causes and immediate consequences", 4, 3),
        ("Key turning points", 3.5, 4),
        ("Interpretations and historiography", 4, 4),
    ],
    "Source Skills": [
        ("Source provenance and utility", 3.5, 4),
        ("Essay planning and argument", 3.5, 4),
        ("Timed essay practice", 4, 4),
    ],
}

_GEOGRAPHY: UnitMap = {
    "Physical Geography": [
        ("Water and carbon cycles", 4, 3),
        ("Coastal systems and landscapes", 3.5, 3),
        ("Hazards: tectonics and storms", 3.5, 3),
    ],
    "Human Geography": [
        ("Global systems and governance", 3.5, 3),
        ("Changing places", 3, 3),
        ("Urban environments", 3.5, 3),
    ],
    "Skills and Fieldwork": [
        ("Statistical and cartographic skills", 3, 3),
        ("Case study revision", 4, 3),
        ("Independent investigation (NEA)", 10, 3),
    ],
}

_GCSE_MATHS: UnitMap = {
    "Number": [
        ("Fractions, decimals and percentages", 2.5, 2),
        ("Indices, surds and standard form", 3, 3),
        ("Ratio and proportion", 3, 2),
        ("Rounding, bounds and estimation", 2, 2),
    ],
    "Algebra": [
        ("Expanding, factorising and rearranging", 3, 2),
        ("Linear equations and inequalities", 3, 2),
        ("Quadratics: solving and graphing", 3.5, 3),
        ("Simultaneous equations", 3, 3),
        ("Sequences", 2.5, 2),
        ("Graphs of functions and transformations", 3.5, 4),
    ],
    "Geometry and Measures": [
        ("Angles, polygons and parallel lines", 2.5, 2),
        ("Pythagoras and trigonometry", 3.5, 3),
        ("Circle theorems", 3.5, 4),
        ("Area, volume and surface area", 3, 2),
        ("Vectors and transformations", 3, 3),
    ],
    "Statistics and Probability": [
        ("Averages and spread", 2, 2),
        ("Charts, histograms and cumulative frequency", 3, 3),
        ("Probability trees and Venn diagrams", 3, 3),
    ],
}

#: Level 2 Further Mathematics, the qualification strong GCSE mathematicians sit
#: alongside GCSE Maths. It needs its own template: without one, the bare
#: "Further Mathematics" fallback below would hand a Year 11 the A Level Core
#: Pure syllabus, complex numbers and hyperbolic functions included.
#:
#: Difficulty runs high because the content genuinely is harder than GCSE Maths,
#: but the hours are deliberately shorter than the full GCSE. It is a
#: supplementary qualification taught to students who already have the
#: underlying material, and hours drive how much of the timetable a subject
#: claims: pitched at GCSE Maths' per-topic rate it would outrank Maths itself.
_GCSE_FURTHER_MATHS: UnitMap = {
    "Algebra": [
        ("Expanding and factorising, including cubics", 2, 3),
        ("Surds, indices and algebraic fractions", 2, 4),
        ("Equations and quadratic inequalities", 2, 3),
        ("Simultaneous equations with a non-linear equation", 2, 4),
        ("The factor theorem", 1.5, 4),
        ("Sequences and the nth term of a quadratic", 1.5, 4),
    ],
    "Functions and Graphs": [
        ("Function notation, domain and range", 1.5, 3),
        ("Composite and inverse functions", 2, 4),
        ("Graphs of quadratics, cubics and reciprocals", 2, 3),
        ("Transformations of graphs", 2, 4),
    ],
    "Coordinate Geometry": [
        ("Straight lines, parallel and perpendicular", 1.5, 2),
        ("The equation of a circle", 1.5, 3),
        ("Tangents to a circle", 2, 4),
    ],
    "Calculus": [
        ("Differentiating polynomials", 2, 3),
        ("Tangents and normals to a curve", 2, 4),
        ("Stationary points and their nature", 2, 4),
    ],
    "Matrices and Transformations": [
        ("Matrix arithmetic and the identity matrix", 1.5, 3),
        ("Matrices as transformations", 2, 4),
        ("Combined transformations and invariant points", 2, 4),
    ],
    "Geometry and Trigonometry": [
        ("Pythagoras and trigonometry in three dimensions", 2, 4),
        ("Sine rule, cosine rule and the area of a triangle", 1.5, 3),
        ("Exact trigonometric values and graphs", 1.5, 3),
        ("Trigonometric equations", 2, 4),
    ],
}

_GCSE_SCIENCE: UnitMap = {
    "Biology": [
        ("Cell biology and transport", 3, 2),
        ("Organisation and digestion", 3, 2),
        ("Infection, response and immunity", 3, 2),
        ("Bioenergetics", 3, 3),
        ("Homeostasis and the nervous system", 3.5, 3),
        ("Inheritance, variation and evolution", 3.5, 3),
        ("Ecology", 3, 2),
    ],
    "Chemistry": [
        ("Atomic structure and the periodic table", 3, 2),
        ("Bonding, structure and properties", 3, 3),
        ("Quantitative chemistry and moles", 3.5, 4),
        ("Chemical changes and electrolysis", 3.5, 3),
        ("Energy changes and rates", 3, 3),
        ("Organic chemistry and polymers", 3, 3),
        ("Chemical analysis and the atmosphere", 3, 2),
    ],
    "Physics": [
        ("Energy stores and transfers", 3, 2),
        ("Electricity and circuits", 3.5, 3),
        ("Particle model and matter", 3, 2),
        ("Atomic structure and radioactivity", 3, 3),
        ("Forces and motion", 3.5, 3),
        ("Waves and the electromagnetic spectrum", 3, 3),
        ("Magnetism and electromagnetism", 3, 3),
    ],
    "Required Practicals": [
        ("Practical method recall", 3, 3),
        ("Analysing practical data", 3, 3),
    ],
}

_GCSE_ENGLISH_LANG: UnitMap = {
    "Reading": [
        ("Identifying and interpreting information", 2.5, 2),
        ("Analysing language and structure", 3.5, 3),
        ("Evaluating texts critically", 3, 3),
        ("Comparing writers' viewpoints", 3.5, 3),
    ],
    "Writing": [
        ("Descriptive and narrative writing", 3.5, 3),
        ("Writing to present a viewpoint", 3.5, 3),
        ("SPaG accuracy drill", 2.5, 2),
    ],
    "Spoken Language": [
        ("Presentation preparation", 2, 1),
    ],
}

_LANGUAGE_GCSE: UnitMap = {
    "Themes": [
        ("Identity and relationships vocabulary", 3, 2),
        ("Local area, holiday and travel", 3, 2),
        ("School and future aspirations", 3, 2),
        ("Global issues and the environment", 3, 3),
    ],
    "Grammar": [
        ("Present and perfect tenses", 3, 3),
        ("Past and imperfect tenses", 3, 3),
        ("Future and conditional tenses", 3, 3),
        ("Pronouns, adjectives and word order", 3, 3),
    ],
    "Skills": [
        ("Listening practice", 3, 3),
        ("Reading and translation", 3, 3),
        ("Speaking: role play and photo card", 3.5, 4),
        ("Writing: 90 and 150 word tasks", 3.5, 3),
    ],
}

_CREATIVE: UnitMap = {
    "Coursework Portfolio": [
        ("Research and idea development", 6, 2),
        ("Experimentation and technique practice", 8, 3),
        ("Refining the final outcome", 8, 3),
        ("Annotation and evaluation", 4, 2),
    ],
    "Exam Component": [
        ("Preparatory studies", 6, 3),
        ("Timed practical exam preparation", 5, 3),
    ],
}

_RS: UnitMap = {
    "Beliefs and Teachings": [
        ("Christianity: beliefs and practices", 3.5, 2),
        ("Islam: beliefs and practices", 3.5, 2),
    ],
    "Thematic Studies": [
        ("Relationships and families", 3, 2),
        ("Religion and life", 3, 2),
        ("Peace and conflict", 3, 3),
        ("Crime and punishment", 3, 3),
    ],
    "Exam Skills": [
        ("12-mark evaluation technique", 3.5, 4),
    ],
}

_ACCOUNTING: UnitMap = {
    "Financial Accounting": [
        ("Double entry bookkeeping", 3.5, 3),
        ("Trial balance and error correction", 3.5, 3),
        ("Final accounts for sole traders", 4, 3),
        ("Depreciation and provisions", 3.5, 4),
        ("Partnership and company accounts", 4.5, 4),
        ("Cash flow statements", 4, 4),
    ],
    "Cost and Management Accounting": [
        ("Costing methods and absorption", 4, 4),
        ("Marginal costing and break-even", 3.5, 3),
        ("Budgeting and variance analysis", 4, 4),
        ("Investment appraisal", 3.5, 4),
    ],
    "Analysis": [
        ("Ratio analysis and interpretation", 4, 4),
        ("Ethics and accounting concepts", 2.5, 2),
    ],
}

_POLITICS: UnitMap = {
    "UK Politics": [
        ("Democracy and participation", 3, 2),
        ("Political parties and elections", 3.5, 3),
        ("Voting behaviour and the media", 3, 3),
    ],
    "UK Government": [
        ("The constitution", 3.5, 3),
        ("Parliament and the executive", 3.5, 3),
        ("Relationships between the branches", 3.5, 4),
    ],
    "Political Ideas": [
        ("Liberalism, conservatism and socialism", 4.5, 4),
        ("Additional idea: feminism / nationalism", 3.5, 4),
        ("Essay technique and thinkers", 4, 4),
    ],
}

_DESIGN_TECH: UnitMap = {
    "Core Technical Principles": [
        ("Materials and their properties", 3, 2),
        ("Energy, forces and mechanical devices", 3, 3),
        ("Manufacturing processes", 3, 3),
        ("Sustainability and ecological issues", 2.5, 2),
    ],
    "Design and Making": [
        ("Design contexts and specifications", 3, 2),
        ("CAD and technical drawing", 3.5, 3),
        ("Prototype development (NEA)", 12, 3),
        ("Testing and evaluation", 3, 2),
    ],
}

_MUSIC: UnitMap = {
    "Listening and Appraising": [
        ("Set works analysis", 4, 3),
        ("Musical elements and vocabulary", 3, 2),
        ("Unfamiliar listening technique", 3, 3),
    ],
    "Performing and Composing": [
        ("Solo performance preparation", 6, 3),
        ("Ensemble performance", 4, 3),
        ("Composition to a brief", 8, 4),
    ],
}


# Curriculum-specific first, then a plain subject-name match.
TEMPLATES: Dict[str, UnitMap] = {
    # --- GCSE -------------------------------------------------------------
    "gcse:Mathematics": _GCSE_MATHS,
    "gcse:Further Mathematics": _GCSE_FURTHER_MATHS,
    "gcse:Combined Science": _GCSE_SCIENCE,
    "gcse:Biology": {"Biology": _GCSE_SCIENCE["Biology"], "Required Practicals": _GCSE_SCIENCE["Required Practicals"]},
    "gcse:Chemistry": {"Chemistry": _GCSE_SCIENCE["Chemistry"], "Required Practicals": _GCSE_SCIENCE["Required Practicals"]},
    "gcse:Physics": {"Physics": _GCSE_SCIENCE["Physics"], "Required Practicals": _GCSE_SCIENCE["Required Practicals"]},
    "gcse:English Language": _GCSE_ENGLISH_LANG,
    "gcse:English Literature": _ENGLISH_LIT,
    "gcse:French": _LANGUAGE_GCSE,
    "gcse:Spanish": _LANGUAGE_GCSE,
    "gcse:German": _LANGUAGE_GCSE,
    "gcse:Art": _CREATIVE,
    "gcse:Music": _MUSIC,
    "gcse:Design Technology": _DESIGN_TECH,
    "gcse:Religious Studies": _RS,
    # --- International A Level --------------------------------------------
    "international_a_level:Pure Mathematics": {
        "Pure Mathematics 1": _MATHS_A_LEVEL["Pure Mathematics 1"],
        "Pure Mathematics 2": _MATHS_A_LEVEL["Pure Mathematics 2"],
    },
    "international_a_level:Mechanics": {"Mechanics": _MATHS_A_LEVEL["Mechanics"]},
    "international_a_level:Statistics": {"Statistics": _MATHS_A_LEVEL["Statistics"]},
    # --- Subject-name fallbacks -------------------------------------------
    "Mathematics": _MATHS_A_LEVEL,
    "Further Mathematics": {
        "Core Pure 1": [
            ("Complex numbers", 4, 4),
            ("Argand diagrams and loci", 4, 5),
            ("Roots of polynomials", 3.5, 4),
            ("Matrices and transformations", 4, 4),
            ("Series and proof by induction", 3.5, 4),
            ("Volumes of revolution", 3.5, 4),
        ],
        "Core Pure 2": [
            ("Further calculus and improper integrals", 4, 5),
            ("Polar coordinates", 3.5, 4),
            ("Hyperbolic functions", 3.5, 4),
            ("Differential equations", 4.5, 5),
            ("Vectors: planes and lines", 4, 4),
        ],
        "Optional Modules": [
            ("Further Mechanics", 5, 5),
            ("Further Statistics", 5, 4),
            ("Decision Mathematics", 4.5, 4),
        ],
    },
    "Physics": _PHYSICS_A_LEVEL,
    "Chemistry": _CHEMISTRY_A_LEVEL,
    "Biology": _BIOLOGY_A_LEVEL,
    "Computer Science": _COMPUTER_SCIENCE,
    "Economics": _ECONOMICS,
    "Business": _BUSINESS,
    "Psychology": _PSYCHOLOGY,
    "English Literature": _ENGLISH_LIT,
    "English Language": _ENGLISH_LANG,
    "History": _HISTORY,
    "Geography": _GEOGRAPHY,
    "Politics": _POLITICS,
    "Accounting": _ACCOUNTING,
    "Pure Mathematics": {
        "Pure Mathematics 1": _MATHS_A_LEVEL["Pure Mathematics 1"],
        "Pure Mathematics 2": _MATHS_A_LEVEL["Pure Mathematics 2"],
    },
    "Mechanics": {"Mechanics": _MATHS_A_LEVEL["Mechanics"]},
    "Statistics": {"Statistics": _MATHS_A_LEVEL["Statistics"]},
    "Religious Studies": _RS,
    "Art": _CREATIVE,
    "Music": _MUSIC,
    "Design Technology": _DESIGN_TECH,
    "French": _LANGUAGE_GCSE,
    "Spanish": _LANGUAGE_GCSE,
    "German": _LANGUAGE_GCSE,
}


_GENERIC: UnitMap = {
    "Foundations": [
        ("Core concepts and key terminology", 3, 2),
        ("Fundamental principles", 3, 2),
        ("Worked examples and practice", 3, 3),
    ],
    "Core Content": [
        ("Main topic area 1", 4, 3),
        ("Main topic area 2", 4, 3),
        ("Main topic area 3", 4, 3),
        ("Applications and case studies", 3.5, 3),
    ],
    "Exam Preparation": [
        ("Past paper technique", 4, 3),
        ("Mark scheme analysis", 3, 3),
        ("Final revision consolidation", 4, 3),
    ],
}


def template_for(subject_name: str, curriculum: str | None = None) -> UnitMap:
    """Return the best-matching syllabus template for a subject."""
    if curriculum:
        keyed = TEMPLATES.get(f"{curriculum}:{subject_name}")
        if keyed:
            return keyed
    return TEMPLATES.get(subject_name, _GENERIC)


def estimated_hours_for(subject_name: str, curriculum: str | None = None) -> float:
    template = template_for(subject_name, curriculum)
    return round(
        sum(hours for topics in template.values() for _, hours, _ in topics), 1
    )


def average_difficulty_for(subject_name: str, curriculum: str | None = None) -> int:
    template = template_for(subject_name, curriculum)
    values = [d for topics in template.values() for _, _, d in topics]
    if not values:
        return 3
    return max(1, min(5, round(sum(values) / len(values))))
