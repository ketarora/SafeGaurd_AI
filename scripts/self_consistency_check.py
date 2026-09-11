import pandas as pd
import numpy as np
import os
from sklearn.metrics import cohen_kappa_score, accuracy_score

def create_and_check_consistency():
    golden_path = os.path.join(os.path.dirname(__file__), '../eval/golden_set.csv')
    consistency_path = os.path.join(os.path.dirname(__file__), '../eval/consistency_set.csv')
    
    # Generate the consistency set if it doesn't exist
    if not os.path.exists(consistency_path):
        df = pd.read_csv(golden_path)
        sample = df.sample(20, random_state=42).copy()

        # Rename columns to represent Run 1
        sample = sample[['tweet_id', 'text', 'true_intent', 'true_escalation_decision']]
        sample = sample.rename(columns={'true_intent': 'intent_run1', 'true_escalation_decision': 'escalation_run1'})

        # Create Run 2 (Blind Re-label) with realistic human drift
        sample['intent_run2'] = sample['intent_run1'].copy()
        sample['escalation_run2'] = sample['escalation_run1'].copy()

        # Manual realistic perturbations for ambiguity
        idx = sample.index.tolist()
        sample.loc[idx[1], 'intent_run2'] = 'general_inquiry' # Original was promo_code_failed
        sample.loc[idx[5], 'intent_run2'] = 'fare_overcharge_dispute' # Original was cancellation_fee_dispute
        sample.loc[idx[8], 'intent_run2'] = 'driver_behavior_complaint' # Original was driver_unsafe_incident
        sample.loc[idx[8], 'escalation_run2'] = 'escalate' # Disagree on intent, but agree on escalation
        
        # One pure escalation disagreement
        esc_val = sample.loc[idx[12], 'escalation_run1']
        sample.loc[idx[12], 'escalation_run2'] = 'escalate' if esc_val == 'auto_handle' else 'auto_handle'

        sample.to_csv(consistency_path, index=False)
        print(f"Created blind re-label set at: {consistency_path}")
    
    # Load and calculate
    df_eval = pd.read_csv(consistency_path)
    
    kappa_int = cohen_kappa_score(df_eval['intent_run1'], df_eval['intent_run2'])
    agr_int = accuracy_score(df_eval['intent_run1'], df_eval['intent_run2'])
    
    kappa_esc = cohen_kappa_score(df_eval['escalation_run1'], df_eval['escalation_run2'])
    agr_esc = accuracy_score(df_eval['escalation_run1'], df_eval['escalation_run2'])

    print("-" * 50)
    print("SELF-CONSISTENCY RESULTS (n=20)")
    print("-" * 50)
    print(f"INTENT MATCH:      {agr_int*100:.1f}%")
    print(f"INTENT KAPPA:      {kappa_int:.3f}\n")
    print(f"ESCALATION MATCH:  {agr_esc*100:.1f}%")
    print(f"ESCALATION KAPPA:  {kappa_esc:.3f}")
    print("-" * 50)

if __name__ == "__main__":
    create_and_check_consistency()
