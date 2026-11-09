CODE FOLDER - HITL ticket classification project

What this folder is
These scripts reproduce the model work and the experiment described in Chapter Three. The main model is DistilBERT (distilbert-base-uncased), a transformer-based encoder model, fine-tuned to classify the tickets. Logistic Regression (TF-IDF) is kept as the baseline it is compared with.
All scripts read the dataset from ../dataset/ (on Kaggle, from the attached dataset) and write their output to the results folder. Only step 4 touches the 20 percent test portion, and only to record the model's predictions.

Cost
Nothing. DistilBERT is trained on Kaggle's free GPU. The other steps run on a laptop.

Requirements
- Laptop (steps 1, 3, 5, 6): Python 3 with scikit-learn, pandas, numpy, scipy, joblib, matplotlib and python-docx.
  Versions used: scikit-learn 1.6.1, pandas 2.3.3.
- Kaggle (steps 2 and 4): nothing to install. Kaggle notebooks already have PyTorch and transformers.
- ticket_model.py with the DistilBERT model also needs:  python3 -m pip install torch transformers

Files and the order to run them
1. 01_model_selection_cross_validation.py   (laptop, a few minutes)
   Baselines: Naive Bayes, Logistic Regression and a calibrated linear SVM, 5-fold cross validation on the training portion only. Also the Logistic Regression confidence bins, thresholds and security rule (the Logistic Regression rows of Tables 3.2, 3.3, 3.5 and 3.6).
   Writes results/cv_results.json and results/lr_cv_predictions.csv.
   Run:  python3 01_model_selection_cross_validation.py

2. 02_transformer_cross_validation.py   (Kaggle GPU, about 50 to 70 minutes)
   DistilBERT with the same split and the same 5 folds. In each fold, 10 percent of the training tickets are kept aside to fit temperature scaling (calibration). Then: confidence bins, thresholds from 50 to 90 percent, the security rule for Administrative rights tickets, and real high, medium and low confidence examples with the words that drove each prediction (Tables 3.2 to 3.6).
   Writes transformer_cv_results.json and transformer_cv_predictions.csv.

3. 03_make_diagram.py   (laptop, seconds)
   Draws the research design diagram (Figure 3.1). Writes results/research_design_diagram.png.
   Run:  python3 03_make_diagram.py

4. 04_final_model_and_test_predictions.py   (Kaggle GPU, about 15 to 20 minutes)
   Fine-tunes DistilBERT once on the whole training portion and predicts every ticket in the 20 percent test portion.
   Writes test_predictions.csv and the folder final_model/.

5. 05_review_conditions_experiment.py   (laptop, a few minutes)
   The experiment. Compares four conditions on the same test tickets:
     AI only | Selective review | Selective review + security rule | Full review
   with the modelled reviewer (overturn and miss rates of 0, 5, 10 and 20 percent, 100 runs each) and the exact McNemar test.
   Writes results/experiment_results.json and results/experiment_summary.csv.
   Run:  python3 05_review_conditions_experiment.py

6. 06_fill_chapter_values.py   (laptop, seconds)
   Chapter Three and the combined Chapters 1-3 file contain yellow placeholders such as [[bert_acc]] wherever a number depends on the Kaggle run. This script fills them from the results and removes the yellow. It first copies the chapters to "untitled folder/previous versions/Before filling results (<date>)".
   Afterwards, read the generated sentences (the script prints them) and reword them in your own words if you wish. A placeholder that stays yellow had no value in the results; the script lists these.
   Run:  python3 06_fill_chapter_values.py

7. 07_chapter4_extra_results.py   (laptop, under a minute)
   Extra results for Chapter Four: AI only results for each category, confidence against accuracy on the test portion, the threshold check (50 to 90 percent) and which part of the security rule sent each extra ticket to review.
   Writes results/chapter4_extra_results.json.
   Run:  python3 07_chapter4_extra_results.py

8. 08_make_chapter4.py   (laptop, seconds)
   Builds "Chapter Four - Results.docx" from the result files, using Chapter Three for the formatting. The survey tables start as [[placeholders]]; step 17 fills them.
   Run:  python3 08_make_chapter4.py

9. 09_make_extra_figures.py   (laptop, seconds)
   Draws Figure 3.2 (routing rules) and Figures 4.1 to 4.4 from the result files. Writes PNG files to results/.
   Run:  python3 09_make_extra_figures.py

10. 10_insert_figures.py   (laptop, seconds)
   Puts the figures from step 9 into the chapter files. Run once on each file; it stops if a figure is already there.
   Run:  python3 10_insert_figures.py

11. 11_make_chapter5.py   (laptop, seconds)
   Builds "Chapter Five - Discussion.docx" (the text is typed in the script) and adds it before the references in a copy of the combined file, "Chapters 1-5 - Introduction to Discussion.docx". It only makes the combined file if it does not exist yet.
   Run:  python3 11_make_chapter5.py

12. 12_make_full_draft.py   (laptop, seconds)
   Builds "Dissertation - Full Draft.docx" from "Chapters 1-6 - Introduction to Conclusion.docx" (so run step 13 first): the front matter (title page with the TU Dublin logo from images/TU Dublin logo.png, declaration, acknowledgements, acronyms, lists of figures and tables, contents and abstract, in the order of the Fergal Connolly template, with black headings and every chapter on a new page), A4 pages, roman page numbers for the front matter and normal numbers from Chapter One, and Appendices A to D (Appendix C, the survey counts, is made from results/survey_results.json). The page numbers in the contents and lists are filled in by step 15. Unknown details are left as [[placeholders]].
   Run:  python3 12_make_full_draft.py

13. 13_make_chapter6.py   (laptop, seconds)
   Builds "Chapter Six - Conclusion.docx" (the text is typed in the script) and adds it before the references in a copy of the combined file, "Chapters 1-6 - Introduction to Conclusion.docx". It only makes the combined file if it does not exist yet. Run it before step 12, then run step 12 again.
   Run:  python3 13_make_chapter6.py

14. 14_template_format.py   (laptop, seconds)
   Formats "Chapters 1-6 - Introduction to Conclusion.docx" like the template theses: headings black instead of Word's default blue, and every chapter starting on a new page. Only the formatting changes, not the text. Other files can be named after the command. Run it again if step 13 recreates the combined file.
   Run:  python3 14_template_format.py

15. 15_update_contents_in_word.py   (laptop with Microsoft Word, seconds)
   Asks Microsoft Word to open "Dissertation - Full Draft.docx", fill in the page numbers in the Contents, List of Figures and List of Tables, set the language to English (UK) for the British spelling check, and save it. Run it after every step 12. If the draft is open in Word it is closed first without saving, so close it yourself first if you have changes to keep.
   Run:  python3 15_update_contents_in_word.py

16. 16_survey_analysis.py   (laptop, seconds; needs openpyxl:  python3 -m pip install --user openpyxl)
   Counts the survey answers (Part B) from the Microsoft Forms export, without changing the export. Only responses where the person agreed to take part and confirmed they are 18 or over are used. Open answers with no content (such as "none" or "Non at the moment") are not counted.
   Writes results/survey_results.json (used by steps 12 and 17).
   Run:  python3 16_survey_analysis.py                          (export in the Project folder)
         python3 16_survey_analysis.py "/path/to/the export.xlsx"   (export kept elsewhere, for example OneDrive)

17. 17_fill_survey_results.py   (laptop, seconds)
   Fills the survey placeholders in "Chapter Four - Results.docx" and the Chapters 1-4 file (Section 4.12, Tables 4.11 to 4.14 and the chapter summary) and removes the yellow. The themes in the open answers were counted by hand and are typed in the script. Back up both files first; it only works on files that still have the placeholders.
   Run:  python3 17_fill_survey_results.py

18. 18_tighten_text.py   (laptop, seconds)
   Tightens the wording of Chapters One to Four so that Chapters 1-6 come to about 16,000 words, puts Sections 3.10 to 3.15 in the past tense, removes the survey pilot, corrects four reference entries (Min et al. 2024, Minaee et al. 2022, and hyphens in two titles) and changes straight quotes to curly ones. Changes the four chapter files and the Chapters 1-4 file. It only works on the versions saved in "Before trimming to 16000 words (2026-11-07)", so restore those first if it needs to be run again. The shorter Chapters Five and Six are typed in steps 11 and 13.
   Run:  python3 18_tighten_text.py

Order when rebuilding everything after a change: 11, 13, 14, 12, 15.
If Chapters One to Four changed, first delete "Chapters 1-5 - Introduction to Discussion.docx" and "Chapters 1-6 - Introduction to Conclusion.docx", because steps 11 and 13 do not replace them if they already exist.

How to run steps 2 and 4 on Kaggle (free)
 1. Sign in at kaggle.com. Verify your phone number once (Settings > Phone verification); this is needed for GPU and internet.
 2. Create > New Notebook.
 3. In the right-hand panel, under Session options: Accelerator = GPU T4 x2 (or GPU T4), Internet = On.
 4. Add Input > search "it-service-ticket-classification-dataset" (by adisongoh) > Add.
 5. Paste the whole of 02_transformer_cross_validation.py into the first cell. Add a second cell and paste the whole of 04_final_model_and_test_predictions.py into it.
 6. Save Version > Save & Run All (Commit). This keeps running even if you close the browser. The whole run takes about 1 to 1.5 hours, which uses about 1.5 of the 30 free GPU hours Kaggle gives each week.
 7. When it finishes, open the saved version > Output, and download everything into this folder's results/ folder: transformer_cv_results.json, transformer_cv_predictions.csv, test_predictions.csv and the final_model folder.
 8. Then, on the laptop, run step 5 and step 6.

Checking the code without a GPU
Setting QUICK_TEST=1 runs a tiny version of step 2 or 4 on a laptop CPU (needs torch and transformers), for example:
   QUICK_TEST=1 python3 02_transformer_cross_validation.py
The figures it produces mean nothing, and step 6 refuses to use them.

ticket_model.py
   The classifier as a tool you can use, with the same review rules as the dissertation.
   Predict for any ticket:   python3 ticket_model.py predict "cannot log in please reset my password"
   It prints the predicted category, the confidence as a percentage, and whether the ticket would go to the human reviewer and why.
   It uses DistilBERT from results/final_model if that folder is there. Otherwise it uses the Logistic Regression baseline, which has to be trained once (about a minute):  python3 ticket_model.py train
   Training saves ticket_model.joblib in this folder. This file can be deleted at any time and recreated by running train again.

Settings to record in the dissertation
- Data split: 80 percent training, 20 percent test, random seed 42, stratified by category.
- Cross validation: 5 folds, random seed 42, on the training portion only. The same folds are used for every model.
- DistilBERT: distilbert-base-uncased; up to 256 word pieces per ticket (1.4 percent of tickets are longer and are cut); AdamW, learning rate 5e-5, weight decay 0.01, 3 epochs, batch size 32, learning rate warm-up over the first 10 percent of steps then linear decay, gradient clipping at 1.0, mixed precision on the GPU. Not tuned.
- Calibration: temperature scaling, with the temperature chosen between 0.50 and 5.00 on 10 percent of each fold's training tickets. Expected calibration error measured with 15 bins.
- Baseline Logistic Regression: TF-IDF with single words and word pairs, terms in fewer than 2 tickets dropped, sublinear term frequency; regularisation strength C = 10, maximum 2,000 iterations. Not tuned.
- General review threshold: 70 percent (thresholds from 50 to 90 percent are also reported).
- Security rule for Administrative rights tickets. A ticket is also sent for review if:
    the model places it in Administrative rights with a confidence below the stricter threshold, or
    the model places it in another category but gives Administrative rights a probability of at least the watch value.
  Stricter thresholds tried: 70, 80, 90, 95 and 99 percent. Watch values tried: none, 1, 2, 5, 10 and 20 percent.
  Targets: at most 1 percent of Administrative rights tickets left wrong without review, and at least 98 percent of the tickets accepted without review as Administrative rights correct.
  The combination that meets both targets with the fewest reviews is chosen on the training portion (step 2) and then applied unchanged to the test portion (step 5). If no combination meets them, the strictest one (99 percent, watch 1 percent) is used and this is reported.
  These targets are a choice: agree them with your supervisor.
- Modelled reviewer: overturn rate and miss rate each 0, 5, 10 and 20 percent; 100 runs per setting.
