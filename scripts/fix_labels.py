import pandas as pd

def fix_labels():
    df = pd.read_csv('eval/golden_set.csv', dtype=str)
    
    intent_map = {
        '1':'promo_code_failed', '2':'receipt_request', '3':'lost_item', 
        '4':'app_technical_bug', '5':'fare_overcharge_dispute', '6':'cancellation_fee_dispute',
        '7':'driver_behavior_complaint', '8':'driver_unsafe_incident', '9':'account_access_issue',
        '0':'general_inquiry'
    }
    df['true_intent'] = df['true_intent'].str.strip().map(intent_map).fillna(df['true_intent'])
    
    esc_map = {
        'y': 'yes', 'n': 'no', 'yes': 'yes', 'no': 'no'
    }
    df['true_escalation_decision'] = df['true_escalation_decision'].str.strip().str.lower().map(esc_map).fillna(df['true_escalation_decision'])
    
    amb_map = {
        '1': 'yes', '0': '', 'y': 'yes', 'n': '', '': ''
    }
    df['ambiguity_flag'] = df['ambiguity_flag'].str.strip().str.lower().map(amb_map).fillna(df['ambiguity_flag'])
    
    df.to_csv('eval/golden_set.csv', index=False)
    print("Labels fixed.")

if __name__ == "__main__":
    fix_labels()
