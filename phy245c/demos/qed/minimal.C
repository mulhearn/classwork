{
  TFile f("demo.root");
  TTree * tree = (TTree *) f.Get("LHEF");
  tree->Print();
}
